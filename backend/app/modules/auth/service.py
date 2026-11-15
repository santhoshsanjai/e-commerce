import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Request, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, NotAuthenticated
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.infrastructure.email import Email
from app.modules.audit import service as audit
from app.modules.auth.models import PasswordResetToken, RefreshToken
from app.modules.auth.schemas import (
    PasswordChange,
    PasswordResetConfirm,
    ProfileUpdate,
    RegisterRequest,
)
from app.modules.users.models import AUDIENCE_FOR, User, UserType


class IssuedTokens:
    def __init__(self, access_token: str, expires_in: int, refresh_token: str) -> None:
        self.access_token = access_token
        self.expires_in = expires_in
        self.refresh_token = refresh_token


def normalise_email(email: str) -> str:
    return email.strip().lower()


def register_buyer(db: Session, data: RegisterRequest) -> User:
    user = User(
        email=normalise_email(data.email),
        full_name=data.full_name,
        phone=data.phone,
        password_hash=hash_password(data.password),
        user_type=UserType.BUYER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "email_taken", "An account with this email already exists", status.HTTP_409_CONFLICT
        ) from exc
    return user


def authenticate(db: Session, email: str, password: str, user_type: UserType) -> User:
    user = db.scalar(select(User).where(User.email == normalise_email(email)))
    valid = verify_password(password, user.password_hash if user else None)
    if not user or not valid or not user.is_active or user.user_type is not user_type:
        raise AppError(
            "invalid_credentials", "Email or password is incorrect", status.HTTP_401_UNAUTHORIZED
        )
    return user


def issue_tokens(db: Session, user: User, family_id: uuid.UUID | None = None) -> IssuedTokens:
    """Create an access token and a new refresh token in the caller's transaction."""
    access, ttl = create_access_token(user.id, AUDIENCE_FOR[user.user_type])
    raw, token_hash = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_ttl_days),
        )
    )
    return IssuedTokens(access, ttl, raw)


def login(
    db: Session, email: str, password: str, user_type: UserType, request: Request
) -> IssuedTokens:
    user = authenticate(db, email, password, user_type)
    return complete_login(db, user, request)


def complete_login(db: Session, user: User, request: Request) -> IssuedTokens:
    """Start a session once every sign-in step has passed. Commits."""
    user.last_login_at = datetime.now(UTC)
    tokens = issue_tokens(db, user)
    if user.user_type is UserType.STAFF:
        audit.record(db, "auth.staff_login", actor_id=user.id, request=request)
    db.commit()
    return tokens


def rotate_refresh_token(db: Session, raw_token: str | None) -> IssuedTokens:
    if not raw_token:
        raise NotAuthenticated("No active session")
    now = datetime.now(UTC)
    stored = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if stored is None:
        raise NotAuthenticated("No active session")
    if stored.revoked_at is not None:
        # A rotated token was presented again: assume theft and end every session in the family.
        _revoke_family(db, stored.family_id, now)
        db.commit()
        raise NotAuthenticated("Session revoked")
    user = db.get(User, stored.user_id)
    if stored.expires_at <= now or user is None or not user.is_active:
        stored.revoked_at = now
        db.commit()
        raise NotAuthenticated("Session expired")
    stored.revoked_at = now
    tokens = issue_tokens(db, user, family_id=stored.family_id)
    db.commit()
    return tokens


def logout(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if stored is not None:
        _revoke_family(db, stored.family_id, datetime.now(UTC))
        db.commit()


def _revoke_family(db: Session, family_id: uuid.UUID, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


STAFF_MIN_PASSWORD = 12


def _check_staff_password_length(user: User, password: str) -> None:
    if user.user_type is UserType.STAFF and len(password) < STAFF_MIN_PASSWORD:
        raise AppError(
            "password_too_short",
            f"Staff passwords need at least {STAFF_MIN_PASSWORD} characters",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


def _revoke_all_sessions(db: Session, user: User, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)
    if data.full_name is not None:
        user.full_name = data.full_name
    if "phone" in changes:
        user.phone = (data.phone or "").strip() or None
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session, user: User, data: PasswordChange, request: Request
) -> IssuedTokens:
    """Check the current password, set the new one, and sign out every other session.

    Returns fresh tokens so the device that made the change stays signed in.
    """
    if not verify_password(data.current_password, user.password_hash):
        raise AppError(
            "wrong_password", "Your current password is incorrect", status.HTTP_400_BAD_REQUEST
        )
    _check_staff_password_length(user, data.new_password)
    if verify_password(data.new_password, user.password_hash):
        raise AppError(
            "password_unchanged",
            "Choose a password you haven't just been using",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    user.password_hash = hash_password(data.new_password)
    _revoke_all_sessions(db, user, datetime.now(UTC))
    tokens = issue_tokens(db, user)
    audit.record(
        db,
        "auth.password_changed",
        actor_id=user.id,
        request=request,
        entity_type="user",
        entity_id=str(user.id),
    )
    db.commit()
    return tokens


def _site_url(user: User) -> str:
    settings = get_settings()
    url = settings.admin_site_url if user.user_type is UserType.STAFF else settings.buyer_site_url
    return url.rstrip("/")


def request_password_reset(db: Session, email: str) -> Email | None:
    """Create a reset link for an active account and return the email to send, or None.

    The caller answers the same way either way, so nobody can learn which emails have accounts.
    A new link cancels any earlier unused ones.
    """
    user = db.scalar(select(User).where(User.email == normalise_email(email)))
    if user is None or not user.is_active or user.password_hash is None:
        return None
    now = datetime.now(UTC)
    ttl = get_settings().password_reset_ttl_minutes
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            expires_at=now + timedelta(minutes=ttl),
        )
    )
    db.commit()
    link = f"{_site_url(user)}/reset-password?token={raw}"
    return Email(
        to=user.email,
        subject="Reset your password",
        text=(
            f"Hello {user.full_name},\n\n"
            f"Someone asked to reset the password for your account. To choose a new password, "
            f"open this link within {ttl} minutes:\n\n{link}\n\n"
            "If you didn't ask for this, you can ignore this email. Your password hasn't changed."
        ),
    )


def _invalid_reset_link() -> AppError:
    return AppError(
        "reset_link_invalid",
        "This reset link has expired or has already been used. Ask for a new one.",
        status.HTTP_400_BAD_REQUEST,
    )


def reset_password(db: Session, data: PasswordResetConfirm, request: Request) -> Email:
    """Set a new password from a reset link and sign out every session.

    Returns a notice to email the person, so they hear about it if it wasn't them.
    """
    now = datetime.now(UTC)
    stored = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_refresh_token(data.token))
        .with_for_update()
    )
    if stored is None or stored.used_at is not None or stored.expires_at <= now:
        raise _invalid_reset_link()
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise _invalid_reset_link()
    _check_staff_password_length(user, data.new_password)
    user.password_hash = hash_password(data.new_password)
    stored.used_at = now
    _revoke_all_sessions(db, user, now)
    audit.record(
        db,
        "auth.password_reset",
        actor_id=user.id,
        request=request,
        entity_type="user",
        entity_id=str(user.id),
    )
    db.commit()
    return password_changed_notice(user)


def password_changed_notice(user: User) -> Email:
    return Email(
        to=user.email,
        subject="Your password was changed",
        text=(
            f"Hello {user.full_name},\n\n"
            "The password for your account was just changed, and every device was signed out.\n\n"
            f"If this wasn't you, reset your password straight away at "
            f"{_site_url(user)}/forgot-password and contact us."
        ),
    )

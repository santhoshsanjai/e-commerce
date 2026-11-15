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
from app.modules.audit import service as audit
from app.modules.auth.models import RefreshToken
from app.modules.auth.schemas import PasswordChange, ProfileUpdate, RegisterRequest
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
    user.last_login_at = datetime.now(UTC)
    tokens = issue_tokens(db, user)
    if user_type is UserType.STAFF:
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
    if user.user_type is UserType.STAFF and len(data.new_password) < STAFF_MIN_PASSWORD:
        raise AppError(
            "password_too_short",
            f"Staff passwords need at least {STAFF_MIN_PASSWORD} characters",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    if verify_password(data.new_password, user.password_hash):
        raise AppError(
            "password_unchanged",
            "Choose a password you haven't just been using",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    user.password_hash = hash_password(data.new_password)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
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

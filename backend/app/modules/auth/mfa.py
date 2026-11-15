"""Two-step sign-in for staff with an authenticator app (TOTP, RFC 6238).

After the password is checked, staff get a short-lived challenge token instead of a session. They
exchange it, plus a code from their app (or a recovery code), for a session. Staff who haven't set
up an app yet are walked through it first.
"""

import hashlib
import hmac
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from fastapi import Request, status
from pyotp.totp import TOTP
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.audit import service as audit
from app.modules.auth.models import MfaRecoveryCode
from app.modules.users.models import User, UserType

Stage = Literal["verify", "enrol"]

CHALLENGE_AUDIENCE = "staff-mfa"
CHALLENGE_TTL_SECONDS = 300
STEP_SECONDS = 30
RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o, 1/l/i look-alikes


# --- secrets at rest -------------------------------------------------------------------------


def _box() -> MultiFernet:
    """MFA_ENCRYPTION_KEY may list several comma-separated keys: the first encrypts, any of them
    decrypts. To rotate, put a new key first, run `python -m app.cli rotate-mfa-key`, then drop
    the old key."""
    keys = [k.strip() for k in get_settings().mfa_encryption_key.split(",") if k.strip()]
    return MultiFernet([Fernet(k) for k in keys])


def reencrypt_all(db: Session) -> int:
    """Re-encrypt every stored secret with the first key. Returns how many accounts changed."""
    box = _box()
    count = 0
    for user in db.scalars(
        select(User).where((User.mfa_secret.is_not(None)) | (User.mfa_pending_secret.is_not(None)))
    ):
        if user.mfa_secret:
            user.mfa_secret = box.rotate(user.mfa_secret.encode()).decode()
        if user.mfa_pending_secret:
            user.mfa_pending_secret = box.rotate(user.mfa_pending_secret.encode()).decode()
        count += 1
    db.commit()
    return count


def _encrypt(secret: str) -> str:
    return _box().encrypt(secret.encode()).decode()


def _decrypt(token: str) -> str:
    try:
        return _box().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # wrong MFA_ENCRYPTION_KEY: an operator problem, not the user's
        raise RuntimeError("MFA secret can't be decrypted; check MFA_ENCRYPTION_KEY") from exc


# --- challenge tokens ------------------------------------------------------------------------


def stage_for(user: User) -> Stage | None:
    """What a staff member must do after the password, or None to sign straight in."""
    if user.mfa_enabled:
        return "verify"
    if get_settings().staff_mfa_required:
        return "enrol"
    return None


def issue_challenge(user: User, stage: Stage) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "aud": CHALLENGE_AUDIENCE,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(seconds=CHALLENGE_TTL_SECONDS),
        "stage": stage,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def _challenge_expired() -> AppError:
    return AppError(
        "mfa_challenge_invalid",
        "Your sign-in timed out. Enter your email and password again.",
        status.HTTP_401_UNAUTHORIZED,
    )


def user_for_challenge(db: Session, token: str, stage: Stage) -> User:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=CHALLENGE_AUDIENCE,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise _challenge_expired() from exc
    user = db.get(User, user_id, with_for_update=True)
    # The stage must still be right: e.g. an enrol challenge is useless once an app is set up.
    if (
        user is None
        or not user.is_active
        or user.user_type is not UserType.STAFF
        or claims.get("stage") != stage
        or stage_for(user) != stage
    ):
        raise _challenge_expired()
    return user


# --- codes -----------------------------------------------------------------------------------


def _matching_step(secret: str, code: str, last_step: int | None) -> int | None:
    """The time step `code` belongs to (allowing one step of clock drift either way), if it is
    newer than the last accepted one."""
    code = code.strip().replace(" ", "")
    if not (len(code) == 6 and code.isdigit()):
        return None
    totp = TOTP(secret)
    now_step = int(time.time()) // STEP_SECONDS
    for step in (now_step - 1, now_step, now_step + 1):
        if hmac.compare_digest(totp.at(step * STEP_SECONDS), code) and (
            last_step is None or step > last_step
        ):
            return step
    return None


def _normalise_recovery(code: str) -> str:
    return "".join(ch for ch in code.lower() if ch.isalnum())


def _hash_recovery(code: str) -> str:
    return hashlib.sha256(_normalise_recovery(code).encode()).hexdigest()


def _new_recovery_codes(db: Session, user: User) -> list[str]:
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id))
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(12))
        code = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"
        codes.append(code)
        db.add(MfaRecoveryCode(user_id=user.id, code_hash=_hash_recovery(code)))
    return codes


def _wrong_code() -> AppError:
    return AppError(
        "mfa_code_invalid",
        "That code isn't right. Enter the 6-digit code your app shows now.",
        status.HTTP_400_BAD_REQUEST,
    )


# --- set up ----------------------------------------------------------------------------------


def start_setup(db: Session, user: User) -> dict[str, str]:
    """Create a new secret for the app to scan. It only takes effect once a code confirms it."""
    secret = pyotp.random_base32()
    user.mfa_pending_secret = _encrypt(secret)
    db.commit()
    uri = TOTP(secret).provisioning_uri(name=user.email, issuer_name=get_settings().mfa_issuer)
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_png": segno.make(uri, error="m").png_data_uri(scale=6, border=2),
    }


def activate(db: Session, user: User, code: str, request: Request) -> list[str]:
    """Confirm the app with a code, turn two-step sign-in on and return fresh recovery codes."""
    if user.mfa_pending_secret is None:
        raise AppError("mfa_not_started", "Start the set-up again.", status.HTTP_400_BAD_REQUEST)
    secret = _decrypt(user.mfa_pending_secret)
    step = _matching_step(secret, code, None)
    if step is None:
        raise _wrong_code()
    user.mfa_secret = user.mfa_pending_secret
    user.mfa_pending_secret = None
    user.mfa_enabled_at = datetime.now(UTC)
    user.mfa_last_step = step
    codes = _new_recovery_codes(db, user)
    audit.record(
        db,
        "auth.mfa_enabled",
        actor_id=user.id,
        request=request,
        entity_type="user",
        entity_id=str(user.id),
    )
    return codes


# --- sign in ---------------------------------------------------------------------------------


def verify(db: Session, user: User, code: str, request: Request) -> None:
    """Accept a current app code, or use up a recovery code. The caller commits."""
    if user.mfa_secret is None:  # stage "verify" guarantees a secret
        raise _challenge_expired()
    step = _matching_step(_decrypt(user.mfa_secret), code, user.mfa_last_step)
    if step is not None:
        user.mfa_last_step = step
        return
    recovery = db.scalar(
        select(MfaRecoveryCode)
        .where(
            MfaRecoveryCode.user_id == user.id,
            MfaRecoveryCode.code_hash == _hash_recovery(code),
            MfaRecoveryCode.used_at.is_(None),
        )
        .with_for_update()
    )
    if recovery is None or len(_normalise_recovery(code)) != 12:
        raise _wrong_code()
    recovery.used_at = datetime.now(UTC)
    audit.record(
        db,
        "auth.mfa_recovery_code_used",
        actor_id=user.id,
        request=request,
        entity_type="user",
        entity_id=str(user.id),
    )


def remaining_recovery_codes(db: Session, user: User) -> int:
    return len(
        db.scalars(
            select(MfaRecoveryCode.id).where(
                MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.used_at.is_(None)
            )
        ).all()
    )


def turn_off(db: Session, user: User) -> None:
    """Remove the app and recovery codes (a Super Admin's reset for a lost phone). The person sets
    up a new app at their next sign-in. The caller commits."""
    user.mfa_secret = None
    user.mfa_pending_secret = None
    user.mfa_enabled_at = None
    user.mfa_last_step = None
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id))

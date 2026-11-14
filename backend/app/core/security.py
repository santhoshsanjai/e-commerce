import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()  # Argon2id with library defaults
# Verified against when the user does not exist, so response time does not reveal valid emails.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: uuid.UUID, audience: str) -> tuple[str, int]:
    settings = get_settings()
    ttl = settings.access_token_ttl_minutes * 60
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "aud": audience,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256"), ttl


def decode_access_token(token: str, audiences: list[str]) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        audience=audiences,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "sub", "aud", "iss"]},
    )


def new_refresh_token() -> tuple[str, str]:
    """Return (raw token for the cookie, SHA-256 hash for the database)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.users.models import UserType


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name is required")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    user_type: UserType
    roles: list[str]
    permissions: list[str]
    mfa_enabled: bool = False


# Same phone rule as delivery addresses; an empty value clears the number.
PHONE = r"^(\+?[0-9][0-9 \-]{8,18}[0-9])?$"


class ProfileUpdate(BaseModel):
    """Fields left out are not changed."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, pattern=PHONE, max_length=32)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Full name is required")
        return value


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=128)


class StaffLoginResponse(BaseModel):
    """Either a session (access_token) or the next sign-in step (mfa + challenge_token)."""

    access_token: str | None = None
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int | None = None
    mfa: Literal["verify", "enrol"] | None = None
    challenge_token: str | None = None


class MfaChallenge(BaseModel):
    challenge_token: str = Field(min_length=1, max_length=2000)


class MfaCode(MfaChallenge):
    code: str = Field(min_length=6, max_length=20)


class MfaSetup(BaseModel):
    secret: str
    otpauth_uri: str
    qr_png: str


class MfaActivated(TokenResponse):
    recovery_codes: list[str]

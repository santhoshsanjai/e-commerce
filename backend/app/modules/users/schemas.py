import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class StaffCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=12, max_length=128)
    role_ids: list[uuid.UUID] = Field(min_length=1)


class StaffUpdate(BaseModel):
    """Fields left out are not changed."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    role_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class StaffStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class StaffOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    roles: list[str]
    role_ids: list[uuid.UUID]
    last_login_at: datetime | None
    created_at: datetime
    mfa_enabled: bool

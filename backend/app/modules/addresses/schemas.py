import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ADR 0006: India only for v1. Six-digit PIN code, first digit 1-9.
PIN_CODE = r"^[1-9][0-9]{5}$"
PHONE = r"^\+?[0-9][0-9 \-]{8,18}[0-9]$"


class AddressIn(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(pattern=PHONE)
    line1: str = Field(min_length=1, max_length=200)
    line2: str = Field(default="", max_length=200)
    landmark: str = Field(default="", max_length=200)
    city: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=100, description="State or union territory")
    postal_code: str = Field(pattern=PIN_CODE)
    is_default: bool = False

    @field_validator("recipient_name", "line1", "line2", "landmark", "city", "region", "phone")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class AddressOut(AddressIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    country_code: str

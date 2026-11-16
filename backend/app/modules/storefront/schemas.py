import re

from pydantic import BaseModel, Field, field_validator

# A design-token name (as in --color-<name>) and a #rrggbb colour.
_TOKEN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_COLORS = 40


class Storefront(BaseModel):
    store_name: str
    announcement: str
    colors: dict[str, str]


class StorefrontUpdate(BaseModel):
    store_name: str = Field(min_length=1, max_length=60)
    announcement: str = Field(default="", max_length=160)
    colors: dict[str, str] = Field(default_factory=dict)

    @field_validator("store_name", "announcement")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("store_name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Enter the shop's name")
        return value

    @field_validator("colors")
    @classmethod
    def _valid_colors(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > MAX_COLORS:
            raise ValueError(f"At most {MAX_COLORS} colours")
        for name, colour in value.items():
            if not _TOKEN.match(name):
                raise ValueError(f"Unknown colour name: {name[:40]}")
            if not _HEX.match(colour):
                raise ValueError(f"{name}: use a colour like #1c2b39")
        return {name: colour.lower() for name, colour in value.items()}

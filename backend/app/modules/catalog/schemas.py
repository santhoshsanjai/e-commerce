import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.catalog.models import MediaType, ProductStatus


class Availability(enum.StrEnum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class ProductSort(enum.StrEnum):
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NAME = "name"


def _strip(value: str) -> str:
    return value.strip()


# ---------- Categories ----------


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    sort_order: int = 0
    is_active: bool = True

    _strip_name = field_validator("name")(_strip)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    sort_order: int
    is_active: bool


# ---------- Products (admin) ----------


class AttributeIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)


class _ProductFields(BaseModel):
    short_description: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=20000)
    attributes: list[AttributeIn] = Field(default_factory=list, max_length=50)


class ProductCreate(_ProductFields):
    name: str = Field(min_length=1, max_length=200)
    category_id: uuid.UUID
    price_minor: int = Field(ge=0, description="Price in minor units, e.g. paise")
    compare_at_minor: int | None = Field(default=None, ge=0)
    stock_qty: int = Field(default=0, ge=0)
    sku: str | None = Field(
        default=None, min_length=1, max_length=64, description="Defaults to the product number"
    )

    _strip_name = field_validator("name")(_strip)

    @model_validator(mode="after")
    def _compare_at_above_price(self) -> "ProductCreate":
        if self.compare_at_minor is not None and self.compare_at_minor <= self.price_minor:
            raise ValueError("compare_at_minor must be greater than price_minor")
        return self


class ProductUpdate(BaseModel):
    """Every field optional. The product number is deliberately absent: it never changes."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=20000)
    attributes: list[AttributeIn] | None = Field(default=None, max_length=50)
    price_minor: int | None = Field(default=None, ge=0)
    compare_at_minor: int | None = Field(default=None, ge=0)
    stock_qty: int | None = Field(default=None, ge=0)


class MediaOut(BaseModel):
    id: uuid.UUID
    type: MediaType
    url: str
    alt_text: str
    width: int | None
    height: int | None
    is_primary: bool
    sort_order: int


class SkuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    price_minor: int
    compare_at_minor: int | None
    currency: str
    stock_qty: int


class AttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    value: str


class AdminProductOut(BaseModel):
    id: uuid.UUID
    product_number: str
    name: str
    slug: str
    status: ProductStatus
    category: CategoryOut
    short_description: str
    description: str
    sku: SkuOut
    attributes: list[AttributeOut]
    media: list[MediaOut]
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminProductListItem(BaseModel):
    id: uuid.UUID
    product_number: str
    name: str
    status: ProductStatus
    category_name: str
    price_minor: int
    currency: str
    stock_qty: int
    primary_image_url: str | None
    updated_at: datetime


# ---------- Products (public) ----------


class ProductCard(BaseModel):
    product_number: str
    name: str
    slug: str
    short_description: str
    price_minor: int
    compare_at_minor: int | None
    currency: str
    availability: Availability
    image_url: str | None
    image_alt: str
    sku_id: uuid.UUID  # the default SKU, so a card can add the product to the cart


class ProductDetail(ProductCard):
    description: str
    category: CategoryOut
    attributes: list[AttributeOut]
    media: list[MediaOut]

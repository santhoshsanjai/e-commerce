import enum
import uuid

from pydantic import BaseModel, Field

from app.modules.cart.models import MAX_LINE_QTY
from app.modules.catalog.schemas import Availability


class LineProblem(enum.StrEnum):
    UNAVAILABLE = "UNAVAILABLE"  # unpublished or archived since it was added
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"


class CartItemAdd(BaseModel):
    sku_id: uuid.UUID
    qty: int = Field(default=1, ge=1, le=MAX_LINE_QTY)


class CartItemUpdate(BaseModel):
    qty: int = Field(ge=1, le=MAX_LINE_QTY)


class CartLine(BaseModel):
    sku_id: uuid.UUID
    product_number: str
    product_name: str
    slug: str
    image_url: str | None
    unit_price_minor: int
    qty: int
    line_total_minor: int
    availability: Availability
    problem: LineProblem | None
    max_qty: int


class CartOut(BaseModel):
    items: list[CartLine]
    item_count: int
    subtotal_minor: int
    shipping_minor: int
    # Added to the total; 0 when prices include GST.
    tax_minor: int
    # All GST in the basket, included in prices or added as tax_minor.
    gst_minor: int
    prices_include_gst: bool
    # Delivery is free once the subtotal reaches this (None: no free delivery).
    free_shipping_over_minor: int | None
    total_minor: int
    currency: str
    can_checkout: bool

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.orders.lifecycle import EventSource, OrderStatus, PaymentMethod, PaymentStatus


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_number: str
    product_name: str
    sku: str
    unit_price_minor: int
    qty: int
    line_total_minor: int
    gst_rate_bp: int
    gst_minor: int


class StatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: OrderStatus | None
    to_status: OrderStatus
    source: EventSource
    reason: str
    occurred_at: datetime


class ShippingAddressOut(BaseModel):
    name: str
    phone: str
    line1: str
    line2: str
    landmark: str
    city: str
    region: str
    postal_code: str
    country_code: str


class OrderSummary(BaseModel):
    order_number: str
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    total_minor: int
    currency: str
    item_count: int
    placed_at: datetime


class OrderDetail(OrderSummary):
    subtotal_minor: int
    shipping_minor: int
    tax_minor: int
    discount_minor: int
    gst_minor: int
    prices_include_gst: bool
    items: list[OrderItemOut]
    shipping_address: ShippingAddressOut
    delivery_instructions: str
    # The courier's tracking number, once the courier file has supplied it.
    awb_number: str | None
    timeline: list[StatusEventOut]
    # The buyer may still cancel it themselves (before handover to the courier).
    can_cancel: bool


class AdminOrderListItem(OrderSummary):
    id: uuid.UUID
    customer_name: str
    ship_phone: str
    ship_city: str


class AdminOrderDetail(OrderDetail):
    id: uuid.UUID
    customer_name: str
    customer_email: str
    # Statuses the lifecycle allows next; anything else needs the override permission.
    allowed_next: list[OrderStatus]


class BuyerCancelIn(BaseModel):
    reason: str = Field(default="", max_length=300)

    @field_validator("reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class StatusChangeIn(BaseModel):
    status: OrderStatus
    reason: str = Field(default="", max_length=500)
    override: bool = False

    @field_validator("reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

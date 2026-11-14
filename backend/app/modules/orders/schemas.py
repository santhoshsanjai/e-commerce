import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.orders.lifecycle import EventSource, OrderStatus, PaymentMethod, PaymentStatus


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_number: str
    product_name: str
    sku: str
    unit_price_minor: int
    qty: int
    line_total_minor: int


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
    items: list[OrderItemOut]
    shipping_address: ShippingAddressOut
    delivery_instructions: str
    timeline: list[StatusEventOut]


class AdminOrderListItem(OrderSummary):
    id: uuid.UUID
    customer_name: str
    ship_phone: str
    ship_city: str


class AdminOrderDetail(OrderDetail):
    id: uuid.UUID
    customer_name: str
    customer_email: str

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.orders.lifecycle import OrderStatus, PaymentStatus
from app.modules.returns.models import RefundMethod, ReturnReason, ReturnStatus


def _strip(value: str) -> str:
    return value.strip()


class ReturnItemIn(BaseModel):
    order_item_id: uuid.UUID
    qty: int = Field(ge=1, le=999)


class ReturnRequestIn(BaseModel):
    items: list[ReturnItemIn] = Field(min_length=1, max_length=50)
    reason: ReturnReason
    note: str = Field(default="", max_length=1000)

    _strip_note = field_validator("note")(_strip)


class ReturnItemOut(BaseModel):
    order_item_id: uuid.UUID
    product_number: str
    product_name: str
    qty: int
    unit_price_minor: int
    restocked: bool


class ReturnOut(BaseModel):
    return_number: str
    order_number: str
    status: ReturnStatus
    reason: ReturnReason
    buyer_note: str
    decision_note: str
    items: list[ReturnItemOut]
    # The value of the returned items at the price paid.
    items_value_minor: int
    refund_minor: int | None
    refund_method: RefundMethod | None
    refund_reference: str
    currency: str
    requested_at: datetime
    decided_at: datetime | None
    received_at: datetime | None
    refunded_at: datetime | None


class ReturnEligibility(BaseModel):
    """What the buyer's order page needs: can they ask for a return, until when, and the
    return they already asked for (if any)."""

    can_request: bool
    deadline: datetime | None
    reason_not: str
    current: ReturnOut | None


class AdminReturnOut(ReturnOut):
    id: uuid.UUID
    order_id: uuid.UUID
    order_status: OrderStatus
    payment_status: PaymentStatus
    order_total_minor: int
    customer_name: str
    customer_email: str
    ship_phone: str


class DecisionIn(BaseModel):
    note: str = Field(default="", max_length=1000)

    _strip_note = field_validator("note")(_strip)


class ReceiveIn(BaseModel):
    # Order item ids to put back on sale; leave out damaged ones.
    restock: list[uuid.UUID] = Field(default_factory=list, max_length=50)


class RefundIn(BaseModel):
    amount_minor: int = Field(gt=0)
    method: RefundMethod
    reference: str = Field(default="", max_length=100)

    _strip_ref = field_validator("reference")(_strip)

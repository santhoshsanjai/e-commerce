import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.orders.schemas import AdminOrderListItem

MAX_BATCH_ORDERS = 500


class CreateBatchIn(BaseModel):
    order_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_BATCH_ORDERS)

    @field_validator("order_ids")
    @classmethod
    def _unique(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Each order can appear only once")
        return value


class DispatchBatchOut(BaseModel):
    id: uuid.UUID
    batch_number: str
    order_count: int
    cod_total_minor: int
    currency: str
    file_name: str
    created_by_name: str | None
    created_at: datetime


class DispatchBatchDetail(DispatchBatchOut):
    orders: list[AdminOrderListItem]

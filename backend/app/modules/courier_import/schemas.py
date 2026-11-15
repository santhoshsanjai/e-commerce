import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.modules.courier_import.models import ImportStatus
from app.modules.orders.lifecycle import OrderStatus

# Preview: will_update, no_change, error. After confirm: updated, no_change, error.
Outcome = Literal["will_update", "updated", "no_change", "error"]


class ImportRowOut(BaseModel):
    row: int
    order_number: str
    awb: str
    courier_status: str
    current_status: OrderStatus | None
    new_status: OrderStatus | None
    outcome: Outcome
    message: str


class CourierImportOut(BaseModel):
    id: uuid.UUID
    file_name: str
    status: ImportStatus
    summary: dict[str, int]
    uploaded_by_name: str | None
    created_at: datetime
    confirmed_at: datetime | None


class CourierImportDetail(CourierImportOut):
    rows: list[ImportRowOut]

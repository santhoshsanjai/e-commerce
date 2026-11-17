import uuid
from datetime import date

from pydantic import BaseModel

from app.modules.orders.lifecycle import OrderStatus


class DaySales(BaseModel):
    day: date
    orders: int
    sales_minor: int


class LowStockItem(BaseModel):
    product_id: uuid.UUID
    product_number: str
    name: str
    stock_qty: int


class Attention(BaseModel):
    awaiting_dispatch: int
    delivery_failed: int
    on_hold: int
    returning: int
    imports_not_applied: int
    # Return requests waiting for staff: to decide, to receive or to refund.
    returns_open: int
    low_stock: list[LowStockItem]


class Dashboard(BaseModel):
    currency: str
    today: DaySales
    last_7_days: list[DaySales]
    cod_with_courier_minor: int
    status_counts: dict[OrderStatus, int]
    attention: Attention

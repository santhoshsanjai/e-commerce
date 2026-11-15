import enum
from datetime import date

from pydantic import BaseModel


class GroupBy(enum.StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class SalesSummary(BaseModel):
    orders: int
    sales_minor: int
    avg_order_minor: int
    items_sold: int
    delivered_orders: int
    delivered_minor: int
    cod_collected_minor: int
    cancelled_orders: int
    cancelled_minor: int
    returned_orders: int
    returned_minor: int


class PeriodRow(BaseModel):
    start: date
    label: str
    orders: int
    sales_minor: int
    items_sold: int


class ProductRow(BaseModel):
    product_number: str
    product_name: str
    qty: int
    sales_minor: int


class RegionRow(BaseModel):
    region: str
    orders: int
    sales_minor: int


class SalesReport(BaseModel):
    currency: str
    date_from: date
    date_to: date
    group_by: GroupBy
    summary: SalesSummary
    periods: list[PeriodRow]
    top_products: list[ProductRow]
    regions: list[RegionRow]

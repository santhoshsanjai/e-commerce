"""Sales reports. Days are Indian calendar days (ADR 0006).

What counts as a sale: an order placed in the range that was not cancelled or returned (the same
rule as the dashboard). Cancelled and returned orders are reported separately so totals reconcile.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from fastapi import status
from sqlalchemy import Date, case, cast, func, literal, select
from sqlalchemy.orm import InstrumentedAttribute, Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.dashboard.service import NOT_SALES
from app.modules.orders.lifecycle import OrderStatus, PaymentStatus
from app.modules.orders.models import Order, OrderItem
from app.modules.reports.schemas import (
    GroupBy,
    PeriodRow,
    ProductRow,
    RegionRow,
    SalesReport,
    SalesSummary,
)
from app.shared.timezones import IST

S = OrderStatus
MAX_DAYS = 366
DEFAULT_DAYS = 30
TOP_PRODUCTS = 10
DELIVERED = (S.DELIVERED, S.COMPLETED)
RETURNED = (S.RETURN_IN_TRANSIT, S.RETURNED)


@dataclass(frozen=True)
class Range:
    date_from: date
    date_to: date

    @property
    def start_utc(self) -> datetime:
        return datetime.combine(self.date_from, time.min, IST).astimezone(UTC)

    @property
    def end_utc(self) -> datetime:
        """Exclusive: midnight at the start of the day after date_to."""
        return datetime.combine(self.date_to + timedelta(days=1), time.min, IST).astimezone(UTC)


def resolve_range(date_from: date | None, date_to: date | None, today: date | None = None) -> Range:
    today = today or datetime.now(IST).date()
    date_to = date_to or today
    date_from = date_from or date_to - timedelta(days=DEFAULT_DAYS - 1)
    if date_from > date_to:
        raise AppError(
            "invalid_range",
            "The start date must be on or before the end date",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    if (date_to - date_from).days + 1 > MAX_DAYS:
        raise AppError(
            "range_too_long",
            f"Choose a range of at most {MAX_DAYS} days",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return Range(date_from, date_to)


def _in_range(r: Range) -> list[ColumnElement[bool]]:
    return [Order.placed_at >= r.start_utc, Order.placed_at < r.end_utc]


def _bucket_start(day: date, group_by: GroupBy) -> date:
    if group_by is GroupBy.WEEK:
        return day - timedelta(days=day.weekday())  # weeks start on Monday
    if group_by is GroupBy.MONTH:
        return day.replace(day=1)
    return day


def _label(start: date, group_by: GroupBy) -> str:
    if group_by is GroupBy.MONTH:
        return start.strftime("%b %Y")
    if group_by is GroupBy.WEEK:
        return "Week of " + start.strftime("%d %b %Y")
    return start.strftime("%d %b %Y")


def _buckets(r: Range, group_by: GroupBy) -> list[date]:
    out: list[date] = []
    day = r.date_from
    while day <= r.date_to:
        start = _bucket_start(day, group_by)
        if not out or out[-1] != start:
            out.append(start)
        day += timedelta(days=1)
    return out


def _sum(expr: ColumnElement[int] | InstrumentedAttribute[int]) -> ColumnElement[int]:
    return func.coalesce(func.sum(expr), 0)


def build(db: Session, r: Range, group_by: GroupBy) -> SalesReport:
    is_sale = Order.status.not_in(NOT_SALES)
    total = Order.total_minor

    def count_if(cond: ColumnElement[bool]) -> ColumnElement[int]:
        return _sum(case((cond, 1), else_=0))

    def value_if(cond: ColumnElement[bool]) -> ColumnElement[int]:
        return _sum(case((cond, total), else_=0))

    agg = db.execute(
        select(
            count_if(is_sale),
            value_if(is_sale),
            count_if(Order.status.in_(DELIVERED)),
            value_if(Order.status.in_(DELIVERED)),
            value_if(Order.payment_status == PaymentStatus.PAID),
            count_if(Order.status == S.CANCELLED),
            value_if(Order.status == S.CANCELLED),
            count_if(Order.status.in_(RETURNED)),
            value_if(Order.status.in_(RETURNED)),
        ).where(*_in_range(r))
    ).one()
    orders, sales = int(agg[0]), int(agg[1])
    items_sold = int(
        db.scalar(
            select(_sum(OrderItem.qty))
            .join(Order, Order.id == OrderItem.order_id)
            .where(*_in_range(r), is_sale)
        )
        or 0
    )
    summary = SalesSummary(
        orders=orders,
        sales_minor=sales,
        avg_order_minor=round(sales / orders) if orders else 0,
        items_sold=items_sold,
        delivered_orders=int(agg[2]),
        delivered_minor=int(agg[3]),
        cod_collected_minor=int(agg[4]),
        cancelled_orders=int(agg[5]),
        cancelled_minor=int(agg[6]),
        returned_orders=int(agg[7]),
        returned_minor=int(agg[8]),
    )

    local_day = cast(func.timezone("Asia/Kolkata", Order.placed_at), Date)
    items_per_order = (
        select(OrderItem.order_id, func.sum(OrderItem.qty).label("qty"))
        .group_by(OrderItem.order_id)
        .subquery()
    )
    day_rows = db.execute(
        select(
            local_day,
            func.count(),
            _sum(total),
            _sum(func.coalesce(items_per_order.c.qty, literal(0))),
        )
        .outerjoin(items_per_order, items_per_order.c.order_id == Order.id)
        .where(*_in_range(r), is_sale)
        .group_by(local_day)
    ).all()
    by_bucket: dict[date, list[int]] = {}
    for day, n, value, qty in day_rows:
        acc = by_bucket.setdefault(_bucket_start(day, group_by), [0, 0, 0])
        acc[0] += n
        acc[1] += int(value)
        acc[2] += int(qty)
    periods = [
        PeriodRow(
            start=start,
            label=_label(start, group_by),
            orders=by_bucket.get(start, [0, 0, 0])[0],
            sales_minor=by_bucket.get(start, [0, 0, 0])[1],
            items_sold=by_bucket.get(start, [0, 0, 0])[2],
        )
        for start in _buckets(r, group_by)
    ]

    return SalesReport(
        currency=get_settings().default_currency,
        date_from=r.date_from,
        date_to=r.date_to,
        group_by=group_by,
        summary=summary,
        periods=periods,
        top_products=products(db, r, limit=TOP_PRODUCTS),
        regions=regions(db, r),
    )


def products(db: Session, r: Range, limit: int | None = None) -> list[ProductRow]:
    revenue = _sum(OrderItem.line_total_minor)
    query = (
        select(
            OrderItem.product_number,
            func.max(OrderItem.product_name),
            _sum(OrderItem.qty),
            revenue,
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(*_in_range(r), Order.status.not_in(NOT_SALES))
        .group_by(OrderItem.product_number)
        .order_by(revenue.desc(), OrderItem.product_number)
    )
    if limit:
        query = query.limit(limit)
    return [
        ProductRow(product_number=pn, product_name=name, qty=int(qty), sales_minor=int(value))
        for pn, name, qty, value in db.execute(query).all()
    ]


def regions(db: Session, r: Range) -> list[RegionRow]:
    value = _sum(Order.total_minor)
    rows = db.execute(
        select(Order.ship_region, func.count(), value)
        .where(*_in_range(r), Order.status.not_in(NOT_SALES))
        .group_by(Order.ship_region)
        .order_by(value.desc(), Order.ship_region)
    ).all()
    return [RegionRow(region=reg, orders=n, sales_minor=int(v)) for reg, n, v in rows]


def orders_in_range(db: Session, r: Range) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(*_in_range(r))
            .order_by(Order.placed_at, Order.id)
        ).all()
    )

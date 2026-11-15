import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.orders.lifecycle import EventSource, OrderStatus, can_transition
from app.modules.orders.models import Order, OrderItem, OrderStatusEvent
from app.modules.orders.schemas import (
    AdminOrderDetail,
    AdminOrderListItem,
    OrderDetail,
    OrderItemOut,
    OrderSummary,
    ShippingAddressOut,
    StatusEventOut,
)
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams


def _summary_fields(order: Order) -> dict[str, object]:
    return {
        "order_number": order.order_number,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "total_minor": order.total_minor,
        "currency": order.currency,
        "item_count": sum(i.qty for i in order.items),
        "placed_at": order.placed_at,
    }


def _detail_fields(order: Order) -> dict[str, object]:
    return {
        **_summary_fields(order),
        "subtotal_minor": order.subtotal_minor,
        "shipping_minor": order.shipping_minor,
        "tax_minor": order.tax_minor,
        "discount_minor": order.discount_minor,
        "items": [OrderItemOut.model_validate(i) for i in order.items],
        "shipping_address": ShippingAddressOut(
            name=order.ship_name,
            phone=order.ship_phone,
            line1=order.ship_line1,
            line2=order.ship_line2,
            landmark=order.ship_landmark,
            city=order.ship_city,
            region=order.ship_region,
            postal_code=order.ship_postal_code,
            country_code=order.ship_country_code,
        ),
        "delivery_instructions": order.delivery_instructions,
        "timeline": [StatusEventOut.model_validate(e) for e in order.events],
    }


def to_detail(order: Order) -> OrderDetail:
    return OrderDetail.model_validate(_detail_fields(order))


def to_admin_detail(order: Order) -> AdminOrderDetail:
    return AdminOrderDetail.model_validate(
        {
            **_detail_fields(order),
            "id": order.id,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
        }
    )


def to_admin_list_item(order: Order) -> AdminOrderListItem:
    return AdminOrderListItem.model_validate(
        {
            **_summary_fields(order),
            "id": order.id,
            "customer_name": order.customer_name,
            "ship_phone": order.ship_phone,
            "ship_city": order.ship_city,
        }
    )


def apply_transition(
    order: Order,
    target: OrderStatus,
    *,
    source: EventSource,
    actor_id: uuid.UUID | None,
    reason: str = "",
    event_key: str | None = None,
    occurred_at: datetime | None = None,
) -> None:
    """Move an order along the lifecycle map and append the history event.

    Callers lock the order row first. Overrides outside the map are a separate, permissioned path.
    """
    if not can_transition(order.status, target):
        raise AppError(
            "invalid_transition",
            f"Order {order.order_number} cannot move from {order.status} to {target}",
            status.HTTP_409_CONFLICT,
            details={"order_number": order.order_number, "from": order.status, "to": target},
        )
    order.events.append(
        OrderStatusEvent(
            from_status=order.status,
            to_status=target,
            source=source,
            reason=reason,
            actor_id=actor_id,
            event_key=event_key,
            occurred_at=occurred_at or datetime.now(UTC),
        )
    )
    order.status = target


# ---------- Buyer ----------


def list_my_orders(db: Session, user: User, params: PageParams) -> Page[OrderSummary]:
    base = select(Order).where(Order.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    orders = db.scalars(
        base.order_by(Order.placed_at.desc()).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(
        items=[OrderSummary.model_validate(_summary_fields(o)) for o in orders],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def get_my_order(db: Session, user: User, order_number: str) -> Order:
    order = db.scalar(
        select(Order).where(Order.order_number == order_number, Order.user_id == user.id)
    )
    if order is None:
        raise AppError("order_not_found", "Order not found", status.HTTP_404_NOT_FOUND)
    return order


# ---------- Admin ----------


def list_admin_orders(
    db: Session,
    params: PageParams,
    q: str | None,
    status_filter: OrderStatus | None,
    date_from: date | None,
    date_to: date | None,
) -> Page[AdminOrderListItem]:
    query = select(Order)
    if q:
        term = q.strip()
        like = f"%{term}%"
        query = query.where(
            or_(
                Order.order_number.ilike(like),
                Order.customer_name.ilike(like),
                Order.ship_name.ilike(like),
                Order.ship_phone.ilike(like),
                Order.customer_email.ilike(like),
                exists().where(
                    OrderItem.order_id == Order.id, OrderItem.product_number.ilike(like)
                ),
            )
        )
    if status_filter:
        query = query.where(Order.status == status_filter)
    # Dates are calendar days in UTC for now; a staff time-zone setting comes later.
    if date_from:
        query = query.where(Order.placed_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(
            Order.placed_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    orders = db.scalars(
        query.order_by(Order.placed_at.desc(), Order.id)
        .offset(params.offset)
        .limit(params.page_size)
    ).all()
    items = [to_admin_list_item(o) for o in orders]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


def get_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise AppError("order_not_found", "Order not found", status.HTTP_404_NOT_FOUND)
    return order

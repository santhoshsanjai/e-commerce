import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import Request, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, PermissionDenied
from app.modules.audit import service as audit
from app.modules.catalog.models import ProductSku
from app.modules.notifications.service import queue_order_email
from app.modules.orders.lifecycle import (
    BUYER_CANCELLABLE,
    CANCELLABLE_WITH_RESTOCK,
    REASON_REQUIRED,
    TRANSITIONS,
    EventSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    can_transition,
)
from app.modules.orders.models import Order, OrderItem, OrderStatusEvent
from app.modules.orders.schemas import (
    AdminOrderDetail,
    AdminOrderListItem,
    OrderDetail,
    OrderItemOut,
    OrderSummary,
    ShippingAddressOut,
    StatusChangeIn,
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
        "gst_minor": order.gst_minor,
        "prices_include_gst": order.prices_include_gst,
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
        "awb_number": order.awb_number,
        "timeline": [StatusEventOut.model_validate(e) for e in order.events],
        "can_cancel": order.status in BUYER_CANCELLABLE,
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
            "allowed_next": sorted(TRANSITIONS[order.status]),
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
    db: Session,
    order: Order,
    target: OrderStatus,
    *,
    source: EventSource,
    actor_id: uuid.UUID | None,
    reason: str = "",
    event_key: str | None = None,
    occurred_at: datetime | None = None,
    override: bool = False,
) -> None:
    """Move an order to `target`, append the history event and apply side effects.

    Callers lock the order row first and check permissions; `override` skips the lifecycle map
    and is only passed for staff holding `orders.status.override`.
    Side effects: cancelling before courier handover puts stock back; a cash-on-delivery order is
    marked paid when delivered; the buyer's email for the change (if any) is queued.
    """
    if target == order.status:
        raise AppError(
            "status_unchanged",
            f"Order {order.order_number} is already {target}",
            status.HTTP_409_CONFLICT,
        )
    if not override and not can_transition(order.status, target):
        raise AppError(
            "invalid_transition",
            f"Order {order.order_number} cannot move from {order.status} to {target}",
            status.HTTP_409_CONFLICT,
            details={
                "order_number": order.order_number,
                "from": order.status,
                "to": target,
                "allowed": sorted(TRANSITIONS[order.status]),
            },
        )
    previous = order.status
    if target == OrderStatus.CANCELLED and previous in CANCELLABLE_WITH_RESTOCK:
        _restock(db, order)
    if target == OrderStatus.DELIVERED and order.payment_method == PaymentMethod.COD:
        order.payment_status = PaymentStatus.PAID
    order.events.append(
        OrderStatusEvent(
            from_status=previous,
            to_status=target,
            source=source,
            reason=reason,
            actor_id=actor_id,
            event_key=event_key,
            occurred_at=occurred_at or datetime.now(UTC),
        )
    )
    order.status = target
    queue_order_email(db, order, previous, target)


def _restock(db: Session, order: Order) -> None:
    sku_ids = sorted({i.sku_id for i in order.items if i.sku_id is not None})
    skus = {
        s.id: s
        for s in db.scalars(
            select(ProductSku)
            .where(ProductSku.id.in_(sku_ids))
            .order_by(ProductSku.id)
            .with_for_update()
        )
    }
    for item in order.items:
        if item.sku_id in skus:
            skus[item.sku_id].stock_qty += item.qty


def get_order_for_update(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise AppError("order_not_found", "Order not found", status.HTTP_404_NOT_FOUND)
    return order


def change_status(
    db: Session,
    order_id: uuid.UUID,
    data: StatusChangeIn,
    actor: User,
    can_override: bool,
    request: Request | None = None,
) -> Order:
    """Manual status change by staff (handoff section 6)."""
    order = get_order_for_update(db, order_id)
    use_override = data.override and not can_transition(order.status, data.status)
    if use_override and not can_override:
        raise PermissionDenied(
            "Overriding the status rules needs the orders.status.override permission"
        )
    if (use_override or data.status in REASON_REQUIRED) and len(data.reason) < 3:
        raise AppError(
            "reason_required",
            "Give a short reason for this change",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    before = {"status": order.status, "payment_status": order.payment_status}
    apply_transition(
        db,
        order,
        data.status,
        source=EventSource.MANUAL,
        actor_id=actor.id,
        reason=data.reason,
        override=use_override,
    )
    audit.record(
        db,
        "order.status_overridden" if use_override else "order.status_changed",
        actor_id=actor.id,
        request=request,
        entity_type="order",
        entity_id=str(order.id),
        before=before,
        after={
            "status": order.status,
            "payment_status": order.payment_status,
            "reason": data.reason,
        },
    )
    db.commit()
    db.refresh(order)
    return order


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


def cancel_by_buyer(
    db: Session, user: User, order_number: str, reason: str, request: Request
) -> Order:
    """A buyer cancels their own order before it is handed to the courier; stock goes back."""
    order = db.scalar(
        select(Order)
        .where(Order.order_number == order_number, Order.user_id == user.id)
        .with_for_update()
    )
    if order is None:
        raise AppError("order_not_found", "Order not found", status.HTTP_404_NOT_FOUND)
    if order.status not in BUYER_CANCELLABLE:
        raise AppError(
            "cannot_cancel",
            "This order is already with the courier, so it can't be cancelled here. "
            "You can return it after delivery.",
            status.HTTP_409_CONFLICT,
        )
    previous = order.status
    apply_transition(
        db,
        order,
        OrderStatus.CANCELLED,
        source=EventSource.BUYER,
        actor_id=user.id,
        reason=f"Cancelled by the buyer{': ' + reason if reason else ''}",
    )
    audit.record(
        db,
        "orders.cancelled_by_buyer",
        actor_id=user.id,
        request=request,
        entity_type="order",
        entity_id=str(order.id),
        before={"status": previous},
        after={"status": OrderStatus.CANCELLED, "reason": reason},
    )
    db.commit()
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

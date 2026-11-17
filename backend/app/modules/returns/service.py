"""Returns and refunds (ADR 0010).

Buyer asks (within the return window after delivery) -> staff approve or reject -> the parcel
comes back and staff put the items they can resell back in stock -> staff record the refund they
paid (cash on delivery orders are refunded by UPI or bank transfer, outside the shop).
The order's own status doesn't change; the return is tracked beside it.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Request, status
from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.audit import service as audit
from app.modules.catalog.models import ProductSku
from app.modules.notifications.service import queue_buyer_email, rupees
from app.modules.orders.lifecycle import OrderStatus, PaymentStatus
from app.modules.orders.models import Order
from app.modules.returns.models import (
    OPEN_STATUSES,
    RefundMethod,
    ReturnItem,
    ReturnReason,
    ReturnRequest,
    ReturnStatus,
)
from app.modules.returns.schemas import (
    AdminReturnOut,
    RefundIn,
    ReturnEligibility,
    ReturnItemOut,
    ReturnOut,
    ReturnRequestIn,
)
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams

RETURNABLE = frozenset({OrderStatus.DELIVERED, OrderStatus.COMPLETED})

REASON_TEXT = {
    ReturnReason.DAMAGED: "Arrived damaged",
    ReturnReason.WRONG_ITEM: "Wrong item sent",
    ReturnReason.NOT_AS_DESCRIBED: "Not as described",
    ReturnReason.NO_LONGER_NEEDED: "No longer needed",
    ReturnReason.OTHER: "Other",
}
METHOD_TEXT = {
    RefundMethod.UPI: "UPI",
    RefundMethod.BANK_TRANSFER: "bank transfer",
    RefundMethod.CASH: "cash",
    RefundMethod.OTHER: "another method",
}


def _conflict(code: str, message: str) -> AppError:
    return AppError(code, message, status.HTTP_409_CONFLICT)


def _not_found() -> AppError:
    return AppError("return_not_found", "Return not found", status.HTTP_404_NOT_FOUND)


# ---------- Output ----------


def _items_value(ret: ReturnRequest) -> int:
    return sum(i.order_item.unit_price_minor * i.qty for i in ret.items)


def _fields(ret: ReturnRequest) -> dict[str, object]:
    return {
        "return_number": ret.return_number,
        "order_number": ret.order.order_number,
        "status": ret.status,
        "reason": ret.reason,
        "buyer_note": ret.buyer_note,
        "decision_note": ret.decision_note,
        "items": [
            ReturnItemOut(
                order_item_id=i.order_item_id,
                product_number=i.order_item.product_number,
                product_name=i.order_item.product_name,
                qty=i.qty,
                unit_price_minor=i.order_item.unit_price_minor,
                restocked=i.restocked,
            )
            for i in ret.items
        ],
        "items_value_minor": _items_value(ret),
        "refund_minor": ret.refund_minor,
        "refund_method": ret.refund_method,
        "refund_reference": ret.refund_reference,
        "currency": ret.order.currency,
        "requested_at": ret.requested_at,
        "decided_at": ret.decided_at,
        "received_at": ret.received_at,
        "refunded_at": ret.refunded_at,
    }


def to_out(ret: ReturnRequest) -> ReturnOut:
    return ReturnOut.model_validate(_fields(ret))


def to_admin_out(ret: ReturnRequest) -> AdminReturnOut:
    o = ret.order
    return AdminReturnOut.model_validate(
        {
            **_fields(ret),
            "id": ret.id,
            "order_id": o.id,
            "order_status": o.status,
            "payment_status": o.payment_status,
            "order_total_minor": o.total_minor,
            "customer_name": o.customer_name,
            "customer_email": o.customer_email,
            "ship_phone": o.ship_phone,
        }
    )


# ---------- Buyer ----------


def _my_order(db: Session, user: User, order_number: str, lock: bool = False) -> Order:
    query = select(Order).where(Order.order_number == order_number, Order.user_id == user.id)
    order = db.scalar(query.with_for_update() if lock else query)
    if order is None:
        raise AppError("order_not_found", "Order not found", status.HTTP_404_NOT_FOUND)
    return order


def _latest_return(db: Session, order: Order) -> ReturnRequest | None:
    return db.scalar(
        select(ReturnRequest)
        .where(ReturnRequest.order_id == order.id)
        .order_by(ReturnRequest.requested_at.desc())
        .limit(1)
    )


def _delivered_at(order: Order) -> datetime | None:
    times = [e.occurred_at for e in order.events if e.to_status == OrderStatus.DELIVERED]
    return max(times) if times else None


def _why_not(
    order: Order, current: ReturnRequest | None, now: datetime
) -> tuple[str, datetime | None]:
    """("", deadline) when a return can be requested, else the reason it can't."""
    delivered = _delivered_at(order)
    deadline = delivered + timedelta(days=get_settings().return_window_days) if delivered else None
    if order.status not in RETURNABLE or deadline is None:
        return "Returns open once the order has been delivered.", None
    if current is not None and current.status in OPEN_STATUSES:
        return "A return for this order is already in progress.", deadline
    if now > deadline:
        return "The return window for this order has closed.", deadline
    return "", deadline


def eligibility(db: Session, user: User, order_number: str) -> ReturnEligibility:
    order = _my_order(db, user, order_number)
    current = _latest_return(db, order)
    reason, deadline = _why_not(order, current, datetime.now(UTC))
    return ReturnEligibility(
        can_request=not reason,
        deadline=deadline,
        reason_not=reason,
        current=to_out(current) if current else None,
    )


def request_return(
    db: Session, user: User, order_number: str, data: ReturnRequestIn, request: Request
) -> ReturnRequest:
    order = _my_order(db, user, order_number, lock=True)
    now = datetime.now(UTC)
    reason, _ = _why_not(order, _latest_return(db, order), now)
    if reason:
        raise _conflict("return_not_allowed", reason)
    by_id = {i.id: i for i in order.items}
    seen: set[uuid.UUID] = set()
    items: list[ReturnItem] = []
    for line in data.items:
        item = by_id.get(line.order_item_id)
        if item is None or line.order_item_id in seen:
            raise AppError("invalid_items", "Choose items from this order, each once")
        if line.qty > item.qty:
            raise AppError(
                "invalid_items", f"You ordered {item.qty} of {item.product_name}; return up to that"
            )
        seen.add(line.order_item_id)
        items.append(ReturnItem(order_item_id=item.id, position=item.position, qty=line.qty))
    number = db.scalar(text("SELECT nextval('return_number_seq')"))
    ret = ReturnRequest(
        return_number=f"RET-{now.year}-{number:06d}",
        order_id=order.id,
        user_id=user.id,
        status=ReturnStatus.REQUESTED,
        reason=data.reason,
        buyer_note=data.note,
        requested_at=now,
        items=sorted(items, key=lambda i: i.position),
    )
    db.add(ret)
    db.flush()
    db.refresh(ret)
    queue_buyer_email(
        db,
        order,
        "return.requested",
        f"Return {ret.return_number} requested",
        f"We've received your request to return items from order {order.order_number} "
        f"({REASON_TEXT[data.reason].lower()}). We'll reply within 2 working days and tell you "
        "how to send them back.\n\n",
    )
    audit.record(
        db,
        "returns.requested",
        actor_id=user.id,
        request=request,
        entity_type="return",
        entity_id=str(ret.id),
        after={"return_number": ret.return_number, "order": order.order_number},
    )
    db.commit()
    return ret


def withdraw(db: Session, user: User, return_number: str, request: Request) -> ReturnRequest:
    ret = db.scalar(
        select(ReturnRequest)
        .where(ReturnRequest.return_number == return_number, ReturnRequest.user_id == user.id)
        .with_for_update(of=ReturnRequest)
    )
    if ret is None:
        raise _not_found()
    if ret.status != ReturnStatus.REQUESTED:
        raise _conflict("return_decided", "This return has already been decided; contact us")
    ret.status = ReturnStatus.WITHDRAWN
    audit.record(
        db,
        "returns.withdrawn",
        actor_id=user.id,
        request=request,
        entity_type="return",
        entity_id=str(ret.id),
    )
    db.commit()
    return ret


# ---------- Staff ----------


def list_returns(
    db: Session, params: PageParams, status_filter: ReturnStatus | None, q: str | None
) -> Page[AdminReturnOut]:
    query: Select[ReturnRequest] = select(ReturnRequest).join(
        Order, Order.id == ReturnRequest.order_id
    )
    if status_filter is not None:
        query = query.where(ReturnRequest.status == status_filter)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            or_(
                ReturnRequest.return_number.ilike(term),
                Order.order_number.ilike(term),
                Order.customer_name.ilike(term),
                Order.ship_phone.ilike(term),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ReturnRequest.requested_at.desc(), ReturnRequest.id)
        .offset(params.offset)
        .limit(params.page_size)
    ).all()
    return Page(
        items=[to_admin_out(r) for r in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def get(db: Session, return_id: uuid.UUID, lock: bool = False) -> ReturnRequest:
    query = select(ReturnRequest).where(ReturnRequest.id == return_id)
    ret = db.scalar(query.with_for_update(of=ReturnRequest) if lock else query)
    if ret is None:
        raise _not_found()
    return ret


def _expect(ret: ReturnRequest, *allowed: ReturnStatus) -> None:
    if ret.status not in allowed:
        raise _conflict(
            "invalid_return_step",
            f"Return {ret.return_number} is {ret.status.value.lower()}; that step isn't possible",
        )


def _record(
    db: Session,
    action: str,
    ret: ReturnRequest,
    actor: User,
    request: Request,
    before: str,
    **after: object,
) -> None:
    audit.record(
        db,
        action,
        actor_id=actor.id,
        request=request,
        entity_type="return",
        entity_id=str(ret.id),
        before={"status": before},
        after={"status": ret.status, **after},
    )


def approve(
    db: Session, return_id: uuid.UUID, note: str, actor: User, request: Request
) -> ReturnRequest:
    ret = get(db, return_id, lock=True)
    _expect(ret, ReturnStatus.REQUESTED)
    before = ret.status
    ret.status = ReturnStatus.APPROVED
    ret.decision_note = note
    ret.decided_at = datetime.now(UTC)
    ret.decided_by = actor.id
    how = f"{note}\n\n" if note else "We'll contact you to arrange the pickup.\n\n"
    queue_buyer_email(
        db,
        ret.order,
        "return.approved",
        f"Return {ret.return_number} approved",
        f"Your return for order {ret.order.order_number} has been approved.\n\n{how}"
        "We'll refund you once the items are back with us.\n\n",
    )
    _record(db, "returns.approved", ret, actor, request, before, note=note)
    db.commit()
    return ret


def reject(
    db: Session, return_id: uuid.UUID, note: str, actor: User, request: Request
) -> ReturnRequest:
    if len(note) < 3:
        raise AppError(
            "reason_required",
            "Tell the buyer why the return can't be accepted",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    ret = get(db, return_id, lock=True)
    _expect(ret, ReturnStatus.REQUESTED)
    before = ret.status
    ret.status = ReturnStatus.REJECTED
    ret.decision_note = note
    ret.decided_at = datetime.now(UTC)
    ret.decided_by = actor.id
    queue_buyer_email(
        db,
        ret.order,
        "return.rejected",
        f"About your return {ret.return_number}",
        f"We're sorry, we can't accept the return for order {ret.order.order_number}.\n\n"
        f"{note}\n\nIf you have questions, reply to this email.\n\n",
    )
    _record(db, "returns.rejected", ret, actor, request, before, note=note)
    db.commit()
    return ret


def receive(
    db: Session, return_id: uuid.UUID, restock: list[uuid.UUID], actor: User, request: Request
) -> ReturnRequest:
    """The parcel is back. Items staff can sell again go back in stock; damaged ones don't."""
    ret = get(db, return_id, lock=True)
    _expect(ret, ReturnStatus.APPROVED)
    wanted = set(restock)
    unknown = wanted - {i.order_item_id for i in ret.items}
    if unknown:
        raise AppError("invalid_items", "Only items in this return can be restocked")
    sku_qty: dict[uuid.UUID, int] = {}
    for item in ret.items:
        if item.order_item_id in wanted and item.order_item.sku_id is not None:
            item.restocked = True
            sku_qty[item.order_item.sku_id] = sku_qty.get(item.order_item.sku_id, 0) + item.qty
    for sku in db.scalars(
        select(ProductSku)
        .where(ProductSku.id.in_(sorted(sku_qty)))
        .order_by(ProductSku.id)
        .with_for_update()
    ):
        sku.stock_qty += sku_qty[sku.id]
    before = ret.status
    ret.status = ReturnStatus.RECEIVED
    ret.received_at = datetime.now(UTC)
    _record(
        db,
        "returns.received",
        ret,
        actor,
        request,
        before,
        restocked=[i.order_item.product_number for i in ret.items if i.restocked],
    )
    db.commit()
    return ret


def refund(
    db: Session, return_id: uuid.UUID, data: RefundIn, actor: User, request: Request
) -> ReturnRequest:
    """Record a refund staff have paid outside the shop (UPI, bank transfer...)."""
    ret = get(db, return_id, lock=True)
    _expect(ret, ReturnStatus.APPROVED, ReturnStatus.RECEIVED)
    order = db.scalar(select(Order).where(Order.id == ret.order_id).with_for_update())
    assert order is not None
    if order.payment_status != PaymentStatus.PAID:
        raise _conflict("not_paid", "This order hasn't been paid, so there's nothing to refund")
    if data.amount_minor > order.total_minor:
        raise AppError(
            "refund_too_large",
            f"The refund can't be more than the order total ({rupees(order.total_minor)})",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    before = ret.status
    ret.status = ReturnStatus.REFUNDED
    ret.refund_minor = data.amount_minor
    ret.refund_method = data.method
    ret.refund_reference = data.reference
    ret.refunded_at = datetime.now(UTC)
    if data.amount_minor == order.total_minor:
        order.payment_status = PaymentStatus.REFUNDED
    ref = f" (reference {data.reference})" if data.reference else ""
    queue_buyer_email(
        db,
        order,
        "return.refunded",
        f"Refund for return {ret.return_number}",
        f"We've refunded {rupees(data.amount_minor)} by {METHOD_TEXT[data.method]}{ref} for "
        f"your return from order {order.order_number}. It can take a few working days to "
        "show in your account.\n\n",
    )
    _record(
        db,
        "returns.refunded",
        ret,
        actor,
        request,
        before,
        amount_minor=data.amount_minor,
        method=data.method,
        reference=data.reference,
    )
    db.commit()
    return ret


def open_count(db: Session) -> int:
    """Returns waiting for staff: asked for, or approved and not yet refunded."""
    return (
        db.scalar(
            select(func.count())
            .select_from(ReturnRequest)
            .where(
                ReturnRequest.status.in_(
                    [ReturnStatus.REQUESTED, ReturnStatus.APPROVED, ReturnStatus.RECEIVED]
                )
            )
        )
        or 0
    )

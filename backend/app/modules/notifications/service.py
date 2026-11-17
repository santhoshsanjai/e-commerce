"""Order emails to buyers, sent through an outbox table.

`queue_order_email` is called inside the transaction that changes the order, so an email exists
only if the change was saved. `deliver_pending` sends what is due: right after the request (as a
background task) and every few minutes from a scheduled task, which also retries failures.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.infrastructure.database import SessionLocal
from app.infrastructure.email import Email, EmailSender
from app.modules.notifications.models import EmailOutbox
from app.modules.orders.lifecycle import OrderStatus
from app.modules.orders.models import Order
from app.modules.storefront import service as storefront

logger = logging.getLogger("app.email")

S = OrderStatus
MAX_ATTEMPTS = 6
BATCH_SIZE = 50
# Sent emails hold names and addresses, so they are not kept longer than needed for support.
KEEP_SENT_FOR = timedelta(days=30)
# Courier files often skip "Dispatched" and go straight to "In transit": both mean "shipped",
# and the buyer hears about it once.
SHIPPED = frozenset({S.DISPATCHED, S.IN_TRANSIT})
NOT_YET_SHIPPED = frozenset(
    {S.PENDING_CONFIRMATION, S.CONFIRMED, S.READY_FOR_DISPATCH, S.EXPORTED_TO_COURIER, S.ON_HOLD}
)


def rupees(minor: int) -> str:
    whole, paise = divmod(minor, 100)
    # Indian digit grouping: 1,23,45,678.
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])
    return f"₹{digits}" if paise == 0 else f"₹{digits}.{paise:02d}"


def _items(order: Order) -> str:
    return "\n".join(
        f"  {i.qty} x {i.product_name} ({i.product_number}): {rupees(i.line_total_minor)}"
        for i in order.items
    )


def _address(order: Order) -> str:
    lines = [order.ship_name, order.ship_line1, order.ship_line2, order.ship_landmark]
    lines.append(f"{order.ship_city}, {order.ship_region} {order.ship_postal_code}")
    return "\n".join(f"  {line}" for line in lines if line)


def _totals(order: Order) -> str:
    rows = [f"  Items: {rupees(order.subtotal_minor)}"]
    if order.discount_minor:
        rows.append(f"  Discount: -{rupees(order.discount_minor)}")
    rows.append(f"  Delivery: {rupees(order.shipping_minor) if order.shipping_minor else 'free'}")
    if order.tax_minor:
        rows.append(f"  GST: {rupees(order.tax_minor)}")
    total = f"  Total: {rupees(order.total_minor)}"
    if order.prices_include_gst and order.gst_minor:
        total += f" (includes GST of {rupees(order.gst_minor)})"
    return "\n".join([*rows, total])


def _compose(order: Order, previous: OrderStatus | None, target: OrderStatus) -> tuple[str, str]:
    """Subject and the message's middle part for a status change, or ("", "") for none."""
    n = order.order_number
    awb = f"\nTracking number (AWB): {order.awb_number}" if order.awb_number else ""
    if target == S.CONFIRMED and previous in (None, S.PENDING_CONFIRMATION):
        pay = (
            f"Please keep {rupees(order.total_minor)} ready to pay in cash when it arrives.\n\n"
            if order.payment_method == "COD"
            else ""
        )
        return (
            f"Order {n} confirmed",
            "Thank you for your order. We've received it and will let you know when it ships.\n\n"
            f"{_items(order)}\n\n{_totals(order)}\n\nDelivering to:\n{_address(order)}\n\n{pay}",
        )
    if target in SHIPPED and (previous is None or previous in NOT_YET_SHIPPED):
        return (f"Order {n} has shipped", f"Your order is on its way.{awb}\n\n{_items(order)}\n\n")
    if target == S.OUT_FOR_DELIVERY:
        cash = (
            f" Please keep {rupees(order.total_minor)} ready to pay in cash."
            if order.payment_method == "COD" and order.payment_status != "PAID"
            else ""
        )
        return (
            f"Order {n} is out for delivery",
            f"Your order will arrive today.{cash}{awb}\n\n",
        )
    if target == S.DELIVERED:
        return (
            f"Order {n} delivered",
            "Your order has been delivered. We hope you enjoy it.\n\n"
            "If something isn't right, reply to this email or contact us from your order page.\n\n",
        )
    if target == S.DELIVERY_FAILED:
        return (
            f"We couldn't deliver order {n}",
            "The courier couldn't deliver your order. They'll usually try again; if you'd like to "
            "change anything, contact us from your order page.\n\n",
        )
    if target == S.CANCELLED:
        return (
            f"Order {n} cancelled",
            "Your order has been cancelled. If you didn't expect this, contact us from your order "
            "page.\n\n",
        )
    if target == S.RETURNED:
        return (
            f"Order {n} returned",
            "Your order has come back to us. We'll be in touch about what happens next.\n\n",
        )
    return ("", "")


def queue_buyer_email(db: Session, order: Order, kind: str, subject: str, middle: str) -> None:
    """Add an email about `order` to its buyer to the outbox, with the shop's name and a link."""
    shop = storefront.get(db).store_name
    link = f"{get_settings().buyer_site_url}/orders/{order.order_number}"
    db.add(
        EmailOutbox(
            kind=kind,
            order=order,
            to_address=order.customer_email,
            subject=f"{subject} · {shop}",
            body=f"Hello {order.customer_name},\n\n{middle}See your order: {link}\n\n{shop}",
        )
    )


def queue_order_email(
    db: Session, order: Order, previous: OrderStatus | None, target: OrderStatus
) -> None:
    """Add the buyer email for this status change, if there is one, to the outbox."""
    subject, middle = _compose(order, previous, target)
    if subject:
        queue_buyer_email(db, order, f"order.{target.value.lower()}", subject, middle)


def _retry_delay(attempts: int) -> timedelta:
    return timedelta(minutes=2 ** min(attempts, 8))


def deliver_pending(sender: EmailSender, limit: int = BATCH_SIZE) -> int:
    """Send due emails; returns how many were sent. Safe to run from several places at once:
    each email is locked while it is being sent."""
    sent = 0
    with SessionLocal() as db:
        while sent < limit:
            row = db.scalar(
                select(EmailOutbox)
                .where(
                    EmailOutbox.sent_at.is_(None),
                    EmailOutbox.attempts < MAX_ATTEMPTS,
                    EmailOutbox.next_attempt_at <= datetime.now(UTC),
                )
                .order_by(EmailOutbox.next_attempt_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if row is None:
                break
            row.attempts += 1
            try:
                sender.send(Email(to=row.to_address, subject=row.subject, text=row.body))
            except Exception as exc:
                row.last_error = f"{type(exc).__name__}: {exc}"[:300]
                row.next_attempt_at = datetime.now(UTC) + _retry_delay(row.attempts)
                logger.warning("Sending email %r failed (attempt %d)", row.subject, row.attempts)
                db.commit()
                continue
            row.sent_at = datetime.now(UTC)
            row.last_error = None
            db.commit()
            sent += 1
    return sent


def deliver_safely(sender: EmailSender) -> None:
    """For background tasks after a request: never raises."""
    try:
        deliver_pending(sender)
    except Exception:
        logger.exception("Delivering queued emails failed")


def purge_sent(db: Session, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(UTC)) - KEEP_SENT_FOR
    result = db.execute(
        delete(EmailOutbox).where(EmailOutbox.sent_at.is_not(None), EmailOutbox.sent_at < cutoff)
    )
    db.commit()
    return int(getattr(result, "rowcount", 0) or 0)

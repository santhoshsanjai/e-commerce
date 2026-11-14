"""Place an order from the buyer's cart.

Everything happens in one transaction: SKU rows are locked (SELECT ... FOR UPDATE, in id order so
two checkouts never deadlock), price and stock are re-checked on the server, stock is decremented,
the order and its item snapshots are written and the cart is emptied. A retried request with the
same Idempotency-Key returns the original order instead of creating a second one.
"""

from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.addresses.service import get_owned
from app.modules.cart.models import Cart
from app.modules.cart.service import line_problem
from app.modules.catalog.models import Product, ProductSku
from app.modules.checkout.schemas import CheckoutRequest
from app.modules.orders.lifecycle import EventSource, OrderStatus, PaymentMethod, PaymentStatus
from app.modules.orders.models import Order, OrderItem, OrderStatusEvent
from app.modules.users.models import User


def _existing(db: Session, user: User, key: str) -> Order | None:
    return db.scalar(select(Order).where(Order.user_id == user.id, Order.idempotency_key == key))


def place_order(
    db: Session, user: User, data: CheckoutRequest, idempotency_key: str
) -> tuple[Order, bool]:
    """Return (order, created). `created` is False when the key was already used."""
    if (order := _existing(db, user, idempotency_key)) is not None:
        return order, False

    address = get_owned(db, user, data.address_id)
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id).with_for_update())
    if cart is None or not cart.items:
        raise AppError("cart_empty", "Your cart is empty")

    qty_by_sku = {item.sku_id: item.qty for item in cart.items}
    skus = db.scalars(
        select(ProductSku)
        .where(ProductSku.id.in_(qty_by_sku))
        .order_by(ProductSku.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    products = {
        p.id: p
        for p in db.scalars(select(Product).where(Product.id.in_({s.product_id for s in skus})))
    }

    problems = []
    for sku in skus:
        problem = line_problem(products[sku.product_id], sku, qty_by_sku[sku.id])
        if problem:
            problems.append(
                {
                    "sku_id": str(sku.id),
                    "product_name": products[sku.product_id].name,
                    "problem": problem.value,
                    "available": sku.stock_qty,
                }
            )
    if len(skus) != len(qty_by_sku) or problems:
        db.rollback()
        raise AppError(
            "cart_changed",
            "Some items in your cart are no longer available in the quantity you chose",
            status.HTTP_409_CONFLICT,
            details=problems,
        )

    settings = get_settings()
    items: list[OrderItem] = []
    for position, item in enumerate(cart.items):
        sku = next(s for s in skus if s.id == item.sku_id)
        product = products[sku.product_id]
        sku.stock_qty -= item.qty
        items.append(
            OrderItem(
                position=position,
                sku_id=sku.id,
                product_number=product.product_number,
                product_name=product.name,
                sku=sku.sku,
                unit_price_minor=sku.price_minor,
                qty=item.qty,
                line_total_minor=sku.price_minor * item.qty,
            )
        )
    subtotal = sum(i.line_total_minor for i in items)
    shipping = settings.shipping_fee_minor
    number = db.scalar(text("SELECT nextval('order_number_seq')"))
    now = datetime.now(UTC)
    # Cash on delivery needs no payment step, so the order is confirmed immediately (ADR 0005).
    initial = (
        OrderStatus.CONFIRMED
        if data.payment_method is PaymentMethod.COD
        else OrderStatus.PENDING_CONFIRMATION
    )
    order = Order(
        order_number=f"ORD-{now.year}-{number:06d}",
        user_id=user.id,
        status=initial,
        payment_method=data.payment_method,
        payment_status=PaymentStatus.PENDING,
        currency=settings.default_currency,
        subtotal_minor=subtotal,
        shipping_minor=shipping,
        tax_minor=0,
        discount_minor=0,
        total_minor=subtotal + shipping,
        customer_name=user.full_name,
        customer_email=user.email,
        ship_name=address.recipient_name,
        ship_phone=address.phone,
        ship_line1=address.line1,
        ship_line2=address.line2,
        ship_landmark=address.landmark,
        ship_city=address.city,
        ship_region=address.region,
        ship_postal_code=address.postal_code,
        ship_country_code=address.country_code,
        delivery_instructions=data.delivery_instructions.strip(),
        idempotency_key=idempotency_key,
        placed_at=now,
        items=items,
        events=[
            OrderStatusEvent(
                from_status=None,
                to_status=initial,
                source=EventSource.BUYER,
                reason="Order placed",
                actor_id=user.id,
                occurred_at=now,
            )
        ],
    )
    db.add(order)
    cart.items.clear()
    try:
        db.commit()
    except IntegrityError:
        # A concurrent request with the same key won the race; return its order.
        db.rollback()
        if (existing := _existing(db, user, idempotency_key)) is not None:
            return existing, False
        raise
    return order, True

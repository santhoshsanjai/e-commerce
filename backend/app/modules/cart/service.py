import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.infrastructure.storage import ObjectStorage
from app.modules.cart.models import MAX_LINE_QTY, Cart, CartItem
from app.modules.cart.schemas import CartItemAdd, CartLine, CartOut, LineProblem
from app.modules.catalog.models import Product, ProductSku, ProductStatus
from app.modules.catalog.service import availability
from app.modules.pricing import service as pricing
from app.modules.users.models import User


def get_or_create_cart(db: Session, user: User, *, lock: bool = False) -> Cart:
    """The buyer's cart, made on first use. Two requests at once (two tabs, or a page loading the
    cart while an item is added) both get the same cart rather than one failing. With lock=True
    the cart row stays locked until commit, so changes to one cart happen one at a time."""
    query = select(Cart).where(Cart.user_id == user.id)
    if lock:
        query = query.with_for_update()
    cart = db.scalars(query).one_or_none()
    if cart is None:
        db.execute(
            insert(Cart)
            .values(id=uuid.uuid4(), user_id=user.id)
            .on_conflict_do_nothing(index_elements=[Cart.user_id])
        )
        cart = db.scalars(query).one()
    return cart


def _purchasable_sku(db: Session, sku_id: uuid.UUID) -> tuple[ProductSku, Product]:
    row = db.execute(
        select(ProductSku, Product)
        .join(Product, Product.id == ProductSku.product_id)
        .where(ProductSku.id == sku_id, Product.status == ProductStatus.PUBLISHED)
    ).first()
    if row is None:
        raise AppError(
            "product_unavailable", "This product is not available", status.HTTP_404_NOT_FOUND
        )
    return row[0], row[1]


def line_problem(product: Product, sku: ProductSku, qty: int) -> LineProblem | None:
    if product.status is not ProductStatus.PUBLISHED:
        return LineProblem.UNAVAILABLE
    if sku.stock_qty <= 0:
        return LineProblem.OUT_OF_STOCK
    if qty > sku.stock_qty:
        return LineProblem.INSUFFICIENT_STOCK
    return None


def add_item(db: Session, user: User, data: CartItemAdd) -> Cart:
    sku, _ = _purchasable_sku(db, data.sku_id)
    cart = get_or_create_cart(db, user, lock=True)
    item = next((i for i in cart.items if i.sku_id == sku.id), None)
    new_qty = (item.qty if item else 0) + data.qty
    limit = min(MAX_LINE_QTY, sku.stock_qty)
    if sku.stock_qty <= 0:
        raise AppError("out_of_stock", "This product is out of stock", status.HTTP_409_CONFLICT)
    if new_qty > limit:
        raise AppError(
            "quantity_unavailable",
            f"You can add at most {limit} of this item",
            status.HTTP_409_CONFLICT,
            details={"max_qty": limit},
        )
    if item:
        item.qty = new_qty
    else:
        cart.items.append(CartItem(sku_id=sku.id, qty=new_qty))
    db.commit()
    return cart


def set_quantity(db: Session, user: User, sku_id: uuid.UUID, qty: int) -> Cart:
    cart = get_or_create_cart(db, user, lock=True)
    item = next((i for i in cart.items if i.sku_id == sku_id), None)
    if item is None:
        raise AppError("not_in_cart", "That item is not in your cart", status.HTTP_404_NOT_FOUND)
    if qty > item.sku.stock_qty:
        raise AppError(
            "quantity_unavailable",
            f"Only {item.sku.stock_qty} left in stock",
            status.HTTP_409_CONFLICT,
            details={"max_qty": item.sku.stock_qty},
        )
    item.qty = qty
    db.commit()
    return cart


def remove_item(db: Session, user: User, sku_id: uuid.UUID) -> Cart:
    cart = get_or_create_cart(db, user, lock=True)
    cart.items = [i for i in cart.items if i.sku_id != sku_id]
    db.commit()
    return cart


def to_out(db: Session, cart: Cart, storage: ObjectStorage) -> CartOut:
    settings = get_settings()
    lines: list[CartLine] = []
    rates: list[int | None] = []
    for item in cart.items:
        product = db.get(Product, item.sku.product_id)
        assert product is not None
        rates.append(product.gst_rate_bp)
        image = product.primary_image
        problem = line_problem(product, item.sku, item.qty)
        lines.append(
            CartLine(
                sku_id=item.sku_id,
                product_number=product.product_number,
                product_name=product.name,
                slug=product.slug,
                image_url=storage.public_url(image.object_key) if image else None,
                unit_price_minor=item.sku.price_minor,
                qty=item.qty,
                line_total_minor=item.sku.price_minor * item.qty,
                availability=availability(item.sku),
                problem=problem,
                max_qty=max(0, min(MAX_LINE_QTY, item.sku.stock_qty)),
            )
        )
    priced = pricing.quote(
        pricing.get(db),
        [
            pricing.Line(line.line_total_minor, rate)
            for line, rate in zip(lines, rates, strict=True)
        ],
    )
    return CartOut(
        items=lines,
        item_count=sum(line.qty for line in lines),
        subtotal_minor=priced.subtotal_minor,
        shipping_minor=priced.shipping_minor,
        tax_minor=priced.tax_minor,
        gst_minor=priced.gst_minor,
        prices_include_gst=priced.prices_include_gst,
        free_shipping_over_minor=priced.free_shipping_over_minor,
        total_minor=priced.total_minor,
        currency=settings.default_currency,
        can_checkout=bool(lines) and all(line.problem is None for line in lines),
    )

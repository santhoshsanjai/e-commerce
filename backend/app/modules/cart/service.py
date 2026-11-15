import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.infrastructure.storage import ObjectStorage
from app.modules.cart.models import MAX_LINE_QTY, Cart, CartItem
from app.modules.cart.schemas import CartItemAdd, CartLine, CartOut, LineProblem
from app.modules.catalog.models import Product, ProductSku, ProductStatus
from app.modules.catalog.service import availability
from app.modules.users.models import User


def get_or_create_cart(db: Session, user: User) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.flush()
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
    cart = get_or_create_cart(db, user)
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
    cart = get_or_create_cart(db, user)
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
    cart = get_or_create_cart(db, user)
    cart.items = [i for i in cart.items if i.sku_id != sku_id]
    db.commit()
    return cart


def to_out(db: Session, cart: Cart, storage: ObjectStorage) -> CartOut:
    settings = get_settings()
    lines: list[CartLine] = []
    for item in cart.items:
        product = db.get(Product, item.sku.product_id)
        assert product is not None
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
    subtotal = sum(line.line_total_minor for line in lines)
    shipping = settings.shipping_fee_minor if lines else 0
    return CartOut(
        items=lines,
        item_count=sum(line.qty for line in lines),
        subtotal_minor=subtotal,
        shipping_minor=shipping,
        total_minor=subtotal + shipping,
        currency=settings.default_currency,
        can_checkout=bool(lines) and all(line.problem is None for line in lines),
    )

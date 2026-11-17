import uuid
from datetime import UTC, datetime
from typing import Any, BinaryIO

from fastapi import Request, status
from sqlalchemy import ColumnElement, Select, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.infrastructure.storage import ObjectStorage
from app.modules.audit import service as audit
from app.modules.catalog.models import (
    Category,
    MediaType,
    Product,
    ProductAttribute,
    ProductMedia,
    ProductSku,
    ProductStatus,
)
from app.modules.catalog.schemas import (
    AdminProductListItem,
    AdminProductOut,
    AttributeOut,
    Availability,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    MediaOut,
    ProductCard,
    ProductCreate,
    ProductDetail,
    ProductSort,
    ProductUpdate,
    SkuOut,
)
from app.modules.media.images import process_image
from app.modules.media.videos import check_video
from app.modules.pricing import service as pricing
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams
from app.shared.text import slugify


def _not_found(what: str) -> AppError:
    return AppError(
        f"{what}_not_found", f"{what.capitalize()} not found", status.HTTP_404_NOT_FOUND
    )


def _unique_slug(db: Session, model: type[Category] | type[Product], base: str) -> str:
    slug, n = base, 2
    while db.scalar(select(model.id).where(model.slug == slug)) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


# ---------- Categories ----------


def list_categories(db: Session, *, active_only: bool) -> list[Category]:
    query = select(Category).order_by(Category.sort_order, Category.name)
    if active_only:
        query = query.where(Category.is_active.is_(True))
    return list(db.scalars(query).all())


def create_category(db: Session, data: CategoryCreate) -> Category:
    if data.parent_id and db.get(Category, data.parent_id) is None:
        raise _not_found("category")
    category = Category(
        name=data.name,
        slug=_unique_slug(db, Category, slugify(data.name)),
        parent_id=data.parent_id,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(category)
    db.commit()
    return category


def update_category(db: Session, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise _not_found("category")
    changes = data.model_dump(exclude_unset=True)
    if "parent_id" in changes and changes["parent_id"] is not None:
        _ensure_no_cycle(db, category.id, changes["parent_id"])
    for field, value in changes.items():
        setattr(category, field, value)
    db.commit()
    return category


def _ensure_no_cycle(db: Session, category_id: uuid.UUID, parent_id: uuid.UUID) -> None:
    current: uuid.UUID | None = parent_id
    while current is not None:
        if current == category_id:
            raise AppError("invalid_parent", "A category cannot be placed inside itself")
        parent = db.get(Category, current)
        if parent is None:
            raise _not_found("category")
        current = parent.parent_id


# ---------- Products: shared helpers ----------


def availability(sku: ProductSku) -> Availability:
    if sku.stock_qty <= 0:
        return Availability.OUT_OF_STOCK
    if sku.stock_qty <= sku.low_stock_threshold:
        return Availability.LOW_STOCK
    return Availability.IN_STOCK


def _media_out(media: ProductMedia, storage: ObjectStorage) -> MediaOut:
    return MediaOut(
        id=media.id,
        type=media.type,
        url=storage.public_url(media.object_key),
        alt_text=media.alt_text,
        width=media.width,
        height=media.height,
        is_primary=media.is_primary,
        sort_order=media.sort_order,
    )


def to_admin_out(product: Product, storage: ObjectStorage) -> AdminProductOut:
    return AdminProductOut(
        id=product.id,
        product_number=product.product_number,
        name=product.name,
        slug=product.slug,
        status=product.status,
        category=CategoryOut.model_validate(product.category),
        short_description=product.short_description,
        description=product.description,
        gst_rate_bp=product.gst_rate_bp,
        sku=SkuOut.model_validate(product.default_sku),
        attributes=[AttributeOut.model_validate(a) for a in product.attributes],
        media=[_media_out(m, storage) for m in product.media],
        published_at=product.published_at,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _card(product: Product, storage: ObjectStorage) -> ProductCard:
    sku = product.default_sku
    image = product.primary_image
    return ProductCard(
        product_number=product.product_number,
        name=product.name,
        slug=product.slug,
        short_description=product.short_description,
        price_minor=sku.price_minor,
        compare_at_minor=sku.compare_at_minor,
        currency=sku.currency,
        availability=availability(sku),
        image_url=storage.public_url(image.object_key) if image else None,
        image_alt=image.alt_text or product.name if image else product.name,
        sku_id=sku.id,
    )


def get_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise _not_found("product")
    return product


def _snapshot(product: Product) -> dict[str, object]:
    sku = product.default_sku
    return {
        "name": product.name,
        "status": product.status.value,
        "category_id": str(product.category_id),
        "price_minor": sku.price_minor,
        "stock_qty": sku.stock_qty,
        "gst_rate_bp": product.gst_rate_bp,
    }


# ---------- Products: admin ----------


def list_admin_products(
    db: Session,
    storage: ObjectStorage,
    params: PageParams,
    q: str | None,
    status_filter: ProductStatus | None,
) -> Page[AdminProductListItem]:
    query = select(Product)
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(Product.name.ilike(term), Product.product_number.ilike(term)))
    if status_filter:
        query = query.where(Product.status == status_filter)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    products = db.scalars(
        query.order_by(Product.updated_at.desc()).offset(params.offset).limit(params.page_size)
    ).all()
    items = []
    for p in products:
        sku, image = p.default_sku, p.primary_image
        items.append(
            AdminProductListItem(
                id=p.id,
                product_number=p.product_number,
                name=p.name,
                status=p.status,
                category_name=p.category.name,
                price_minor=sku.price_minor,
                currency=sku.currency,
                stock_qty=sku.stock_qty,
                primary_image_url=storage.public_url(image.object_key) if image else None,
                updated_at=p.updated_at,
            )
        )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


def create_product(db: Session, data: ProductCreate, actor: User, request: Request) -> Product:
    if db.get(Category, data.category_id) is None:
        raise _not_found("category")
    number = db.scalar(text("SELECT nextval('product_number_seq')"))
    product_number = f"P-{number:06d}"
    sku_code = (data.sku or product_number).strip()
    if db.scalar(select(ProductSku.id).where(ProductSku.sku == sku_code)) is not None:
        raise AppError("sku_taken", "That SKU is already used", status.HTTP_409_CONFLICT)
    product = Product(
        product_number=product_number,
        name=data.name,
        slug=_unique_slug(db, Product, slugify(data.name)),
        category_id=data.category_id,
        short_description=data.short_description,
        description=data.description,
        gst_rate_bp=data.gst_rate_bp,
        created_by=actor.id,
        updated_by=actor.id,
        skus=[
            ProductSku(
                sku=sku_code,
                price_minor=data.price_minor,
                compare_at_minor=data.compare_at_minor,
                currency=get_settings().default_currency,
                stock_qty=data.stock_qty,
                is_default=True,
            )
        ],
        attributes=[
            ProductAttribute(name=a.name, value=a.value, sort_order=i)
            for i, a in enumerate(data.attributes)
        ],
    )
    db.add(product)
    db.flush()
    audit.record(
        db,
        "products.created",
        actor_id=actor.id,
        request=request,
        entity_type="product",
        entity_id=str(product.id),
        after=_snapshot(product),
    )
    db.commit()
    return product


def update_product(
    db: Session, product_id: uuid.UUID, data: ProductUpdate, actor: User, request: Request
) -> Product:
    product = get_product(db, product_id)
    if product.status is ProductStatus.ARCHIVED:
        raise AppError("product_archived", "Archived products cannot be edited")
    before = _snapshot(product)
    changes = data.model_dump(exclude_unset=True)
    sku = product.default_sku

    if "category_id" in changes:
        if changes["category_id"] is None or db.get(Category, changes["category_id"]) is None:
            raise _not_found("category")
        product.category_id = changes["category_id"]
    for field in ("name", "short_description", "description"):
        if field in changes and changes[field] is not None:
            setattr(product, field, changes[field].strip() if field == "name" else changes[field])
    if "gst_rate_bp" in changes:
        product.gst_rate_bp = changes["gst_rate_bp"]
    if "attributes" in changes and data.attributes is not None:
        product.attributes = [
            ProductAttribute(name=a.name, value=a.value, sort_order=i)
            for i, a in enumerate(data.attributes)
        ]
    for field in ("price_minor", "compare_at_minor", "stock_qty"):
        if field in changes and (changes[field] is not None or field == "compare_at_minor"):
            setattr(sku, field, changes[field])
    if sku.compare_at_minor is not None and sku.compare_at_minor <= sku.price_minor:
        raise AppError(
            "invalid_compare_at", "Compare-at price must be greater than the selling price"
        )
    product.updated_by = actor.id
    db.flush()
    audit.record(
        db,
        "products.updated",
        actor_id=actor.id,
        request=request,
        entity_type="product",
        entity_id=str(product.id),
        before=before,
        after=_snapshot(product),
    )
    db.commit()
    db.refresh(product)
    return product


def set_status(
    db: Session, product_id: uuid.UUID, target: ProductStatus, actor: User, request: Request
) -> Product:
    product = get_product(db, product_id)
    if product.status is ProductStatus.ARCHIVED and target is not ProductStatus.ARCHIVED:
        raise AppError("product_archived", "Archived products cannot be republished")
    if target is ProductStatus.PUBLISHED:
        problems = []
        if not product.category.is_active:
            problems.append("its category is inactive")
        if product.primary_image is None:
            problems.append("it has no primary image")
        if product.default_sku.price_minor <= 0:
            problems.append("its price is zero")
        if problems:
            raise AppError(
                "not_publishable",
                "This product cannot be published yet: " + "; ".join(problems),
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
    before = product.status
    product.status = target
    if target is ProductStatus.PUBLISHED and product.published_at is None:
        product.published_at = datetime.now(UTC)
    product.updated_by = actor.id
    audit.record(
        db,
        f"products.{target.value.lower()}",
        actor_id=actor.id,
        request=request,
        entity_type="product",
        entity_id=str(product.id),
        before={"status": before.value},
        after={"status": target.value},
    )
    db.commit()
    return product


def add_image(
    db: Session,
    storage: ObjectStorage,
    product_id: uuid.UUID,
    raw: bytes,
    alt_text: str,
    actor: User,
) -> Product:
    product = get_product(db, product_id)
    image = process_image(raw, get_settings().max_image_bytes)
    key = f"products/{product.id}/{uuid.uuid4().hex}.{image.extension}"
    storage.put(key, image.data, image.mime_type)
    product.media.append(
        ProductMedia(
            type=MediaType.IMAGE,
            object_key=key,
            mime_type=image.mime_type,
            size_bytes=len(image.data),
            width=image.width,
            height=image.height,
            alt_text=alt_text.strip()[:300],
            sort_order=len(product.media),
            is_primary=product.primary_image is None,
        )
    )
    product.updated_by = actor.id
    db.commit()
    db.refresh(product)
    return product


MAX_VIDEOS = 3


def add_video(
    db: Session,
    storage: ObjectStorage,
    product_id: uuid.UUID,
    file: BinaryIO,
    size: int,
    alt_text: str,
    actor: User,
) -> Product:
    product = get_product(db, product_id)
    if product.status is ProductStatus.ARCHIVED:
        raise AppError("product_archived", "Archived products cannot be edited")
    if sum(m.type is MediaType.VIDEO for m in product.media) >= MAX_VIDEOS:
        raise AppError(
            "too_many_videos",
            f"A product can have at most {MAX_VIDEOS} videos",
            status.HTTP_409_CONFLICT,
        )
    kind = check_video(file.read(64))
    file.seek(0)
    key = f"products/{product.id}/{uuid.uuid4().hex}.{kind.extension}"
    storage.put_file(key, file, kind.mime_type)
    product.media.append(
        ProductMedia(
            type=MediaType.VIDEO,
            object_key=key,
            mime_type=kind.mime_type,
            size_bytes=size,
            alt_text=alt_text.strip()[:300],
            sort_order=len(product.media),
            is_primary=False,
        )
    )
    product.updated_by = actor.id
    try:
        db.commit()
    except Exception:
        storage.delete(key)
        raise
    db.refresh(product)
    return product


def remove_media(
    db: Session, storage: ObjectStorage, product_id: uuid.UUID, media_id: uuid.UUID, actor: User
) -> Product:
    product = get_product(db, product_id)
    media = next((m for m in product.media if m.id == media_id), None)
    if media is None:
        raise _not_found("media")
    images = [m for m in product.media if m.type is MediaType.IMAGE]
    if product.status is ProductStatus.PUBLISHED and media.is_primary and len(images) == 1:
        raise AppError("last_image", "A published product must keep at least one image")
    was_primary = media.is_primary
    product.media.remove(media)
    db.flush()
    next_image = next((m for m in product.media if m.type is MediaType.IMAGE), None)
    if was_primary and next_image is not None:
        next_image.is_primary = True
    product.updated_by = actor.id
    db.commit()
    storage.delete(media.object_key)
    db.refresh(product)
    return product


# ---------- Products: public catalogue ----------


def _published() -> Select[Product]:
    return select(Product).where(Product.status == ProductStatus.PUBLISHED)


def search_products(
    db: Session,
    storage: ObjectStorage,
    params: PageParams,
    q: str | None,
    category_slug: str | None,
    sort: ProductSort,
) -> Page[ProductCard]:
    query = _published().join(
        ProductSku, (ProductSku.product_id == Product.id) & ProductSku.is_default
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(Product.name.ilike(term), Product.product_number.ilike(term)))
    if category_slug:
        category = db.scalar(
            select(Category).where(Category.slug == category_slug, Category.is_active.is_(True))
        )
        if category is None:
            return Page(items=[], total=0, page=params.page, page_size=params.page_size)
        ids = _descendant_ids(db, category.id)
        query = query.where(Product.category_id.in_(ids))
    sort_columns: dict[ProductSort, ColumnElement[Any]] = {
        ProductSort.NEWEST: Product.published_at.desc(),
        ProductSort.PRICE_ASC: ProductSku.price_minor.asc(),
        ProductSort.PRICE_DESC: ProductSku.price_minor.desc(),
        ProductSort.NAME: Product.name.asc(),
    }
    # Product.id as a tie-breaker keeps pagination stable.
    order = [sort_columns[sort], Product.id.asc()]
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    products = db.scalars(
        query.order_by(*order).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(
        items=[_card(p, storage) for p in products],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def _descendant_ids(db: Session, root_id: uuid.UUID) -> list[uuid.UUID]:
    rows = db.execute(
        text(
            """
            WITH RECURSIVE tree AS (
                SELECT id FROM categories WHERE id = :root
                UNION ALL
                SELECT c.id FROM categories c JOIN tree t ON c.parent_id = t.id
                WHERE c.is_active
            )
            SELECT id FROM tree
            """
        ),
        {"root": root_id},
    )
    return [row[0] for row in rows]


def get_published_by_slug(db: Session, storage: ObjectStorage, slug: str) -> ProductDetail:
    """Kept for old /products/{slug} links; the shop now looks products up by number."""
    product = db.scalar(_published().where(Product.slug == slug))
    if product is None:
        raise _not_found("product")
    return _detail(db, product, storage)


def get_published_by_number(
    db: Session, storage: ObjectStorage, product_number: str
) -> ProductDetail:
    """The product number never changes, unlike the name and slug, so links use it."""
    product = db.scalar(_published().where(Product.product_number == product_number.upper()))
    if product is None:
        raise _not_found("product")
    return _detail(db, product, storage)


def _detail(db: Session, product: Product, storage: ObjectStorage) -> ProductDetail:
    card = _card(product, storage)
    return ProductDetail(
        prices_include_gst=pricing.get(db).prices_include_gst,
        **card.model_dump(),
        description=product.description,
        category=CategoryOut.model_validate(product.category),
        attributes=[AttributeOut.model_validate(a) for a in product.attributes],
        media=[_media_out(m, storage) for m in product.media],
    )

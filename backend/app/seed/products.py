"""Load the sample catalogue into the database, with a picture for every product.

Safe to run more than once: products are matched by their SKU (SAMPLE-001 to SAMPLE-050) and
categories and brands by slug, so a second run adds only what is missing and never changes or
duplicates what is already there, including anything staff have edited since.
"""

import math
from datetime import UTC, datetime, timedelta
from itertools import zip_longest

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.infrastructure.storage import ObjectStorage
from app.modules.catalog.models import (
    Brand,
    Category,
    MediaType,
    Product,
    ProductAttribute,
    ProductMedia,
    ProductSku,
    ProductStatus,
)
from app.seed import images
from app.seed.catalogue import BRANDS, CATEGORIES, PRODUCTS, SampleProduct
from app.shared.text import slugify

SKU_PREFIX = "SAMPLE-"
# Prices are written in pounds. For a shop that sells in rupees they are converted at this rate
# and rounded to a price ending in 99.
GBP_TO_INR = 110


def _price(pence: int, currency: str) -> int:
    if currency != "INR":
        return pence
    rupees = math.ceil(pence / 100 * GBP_TO_INR / 100) * 100 - 1
    return rupees * 100


def _unique_slug(db: Session, base: str) -> str:
    slug, n = base, 2
    while db.scalar(select(Product.id).where(Product.slug == slug)) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


def _interleaved() -> list[tuple[int, SampleProduct]]:
    """Products numbered 1 to 50, ordered so that every category appears among the newest."""
    by_category = [
        [(i, p) for i, p in enumerate(PRODUCTS, start=1) if p.category == c.slug]
        for c in CATEGORIES
    ]
    return [item for row in zip_longest(*by_category) for item in row if item is not None]


def seed(db: Session, storage: ObjectStorage) -> tuple[int, int]:
    """Returns (products added, products already present)."""
    currency = get_settings().default_currency

    categories: dict[str, Category] = {}
    for order, c in enumerate(CATEGORIES):
        category = db.scalar(select(Category).where(Category.slug == c.slug))
        if category is None:
            category = Category(name=c.name, slug=c.slug, sort_order=order, is_active=True)
            db.add(category)
        categories[c.slug] = category

    brands: dict[str, Brand] = {}
    for name in BRANDS:
        brand = db.scalar(select(Brand).where(Brand.slug == slugify(name)))
        if brand is None:
            brand = db.scalar(select(Brand).where(Brand.name == name))
        if brand is None:
            brand = Brand(name=name, slug=slugify(name))
            db.add(brand)
        brands[name] = brand
    db.flush()

    backdrops = {c.slug: c.backdrop for c in CATEGORIES}
    now = datetime.now(UTC)
    added = present = 0
    for position, (number, p) in enumerate(_interleaved()):
        sku_code = f"{SKU_PREFIX}{number:03d}"
        if db.scalar(select(ProductSku.id).where(ProductSku.sku == sku_code)) is not None:
            present += 1
            continue
        seq = db.scalar(text("SELECT nextval('product_number_seq')"))
        published = now - timedelta(hours=3 * position)
        product = Product(
            product_number=f"P-{seq:06d}",
            name=p.name,
            slug=_unique_slug(db, slugify(p.name)),
            category_id=categories[p.category].id,
            brand_id=brands[p.brand].id,
            short_description=p.short,
            description=p.description,
            status=ProductStatus.PUBLISHED,
            published_at=published,
            skus=[
                ProductSku(
                    sku=sku_code,
                    price_minor=_price(p.price, currency),
                    compare_at_minor=_price(p.compare_at, currency) if p.compare_at else None,
                    currency=currency,
                    stock_qty=p.stock,
                    is_default=True,
                )
            ],
            attributes=[
                ProductAttribute(name=k, value=v, sort_order=i)
                for i, (k, v) in enumerate(p.attributes.items())
            ],
        )
        db.add(product)
        db.flush()

        picture = images.draw(p.kind, p.color, p.accent, backdrops[p.category])
        key = f"products/{product.id}/sample.jpg"
        storage.put(key, picture, "image/jpeg")
        product.media.append(
            ProductMedia(
                type=MediaType.IMAGE,
                object_key=key,
                mime_type="image/jpeg",
                size_bytes=len(picture),
                width=images.SIZE,
                height=images.SIZE,
                alt_text=p.name,
                sort_order=0,
                is_primary=True,
            )
        )
        db.commit()
        added += 1
    db.commit()
    return added, present

import io

from PIL import Image
from sqlalchemy import func, select

from app.infrastructure.database import SessionLocal
from app.modules.catalog.models import Category, Product, ProductSku, ProductStatus
from app.seed import images
from app.seed.catalogue import CATEGORIES, PRODUCTS
from app.seed.products import _price, seed


def test_every_product_has_a_drawing() -> None:
    assert len(PRODUCTS) == 50
    assert {p.category for p in PRODUCTS} == {c.slug for c in CATEGORIES}
    assert all(p.kind in images.DRAWERS for p in PRODUCTS)
    picture = Image.open(io.BytesIO(images.draw("mug", "#1f3a5f", "#c9a227", "#eeeeee")))
    assert picture.format == "JPEG" and picture.size == (images.SIZE, images.SIZE)


def test_prices_convert_to_rupees_ending_in_99() -> None:
    assert _price(2800, "GBP") == 2800
    assert _price(2800, "INR") == 309900


def test_seed_adds_50_published_products_once(client, storage) -> None:
    with SessionLocal() as db:
        db.add(Category(name="Home & Living", slug="home-living"))
        db.commit()
        assert seed(db, storage) == (50, 0)
        assert seed(db, storage) == (0, 50)
        assert db.scalar(select(func.count()).select_from(Product)) == 50
        assert db.scalar(select(func.count()).select_from(Category)) == 5
        assert (
            db.scalar(
                select(func.count()).select_from(ProductSku).where(ProductSku.sku.like("SAMPLE-%"))
            )
            == 50
        )
        assert all(
            p.status == ProductStatus.PUBLISHED and p.primary_image is not None
            for p in db.scalars(select(Product))
        )
        # The home page's newest products cover every category.
        newest = db.scalars(select(Product).order_by(Product.published_at.desc()).limit(5))
        assert len({p.category_id for p in newest}) == 5
    assert len(storage.objects) == 50

    shop = client.get("/api/v1/products", params={"sort": "newest", "page_size": 12}).json()
    assert shop["total"] == 50
    assert all(item["image_url"] for item in shop["items"])

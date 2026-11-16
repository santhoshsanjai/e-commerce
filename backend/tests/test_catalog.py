import io

import pytest
from PIL import Image


def png_bytes(color: str = "red", size: tuple[int, int] = (40, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def jpeg_with_exif() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (20, 20), "blue")
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


@pytest.fixture
def admin(client, staff_token):
    return {"Authorization": f"Bearer {staff_token('Admin')}"}


@pytest.fixture
def category(client, admin):
    resp = client.post("/api/v1/admin/categories", json={"name": "Home & Kitchen"}, headers=admin)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_product(client, admin, category, **overrides):
    payload = {
        "name": "Steel Water Bottle",
        "category_id": category["id"],
        "price_minor": 49900,
        "stock_qty": 20,
        "short_description": "1 litre, keeps drinks cold",
        "attributes": [{"name": "Capacity", "value": "1 L"}],
        **overrides,
    }
    resp = client.post("/api/v1/admin/products", json=payload, headers=admin)
    assert resp.status_code == 201, resp.text
    return resp.json()


def upload(client, admin, product_id, data=None, name="photo.png", content_type="image/png"):
    return client.post(
        f"/api/v1/admin/products/{product_id}/media",
        files={"file": (name, data if data is not None else png_bytes(), content_type)},
        data={"alt_text": "Bottle front"},
        headers=admin,
    )


def publish(client, admin, product_id):
    return client.post(f"/api/v1/admin/products/{product_id}/publish", headers=admin)


# ---------- Categories ----------


def test_category_slug_is_generated_and_unique(client, admin, category):
    assert category["slug"] == "home-kitchen"
    second = client.post("/api/v1/admin/categories", json={"name": "Home & Kitchen"}, headers=admin)
    assert second.json()["slug"] == "home-kitchen-2"


def test_category_cannot_be_its_own_ancestor(client, admin, category):
    child = client.post(
        "/api/v1/admin/categories",
        json={"name": "Bottles", "parent_id": category["id"]},
        headers=admin,
    ).json()
    resp = client.patch(
        f"/api/v1/admin/categories/{category['id']}", json={"parent_id": child["id"]}, headers=admin
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_parent"


def test_public_categories_hide_inactive(client, admin, category):
    client.patch(
        f"/api/v1/admin/categories/{category['id']}", json={"is_active": False}, headers=admin
    )
    assert client.get("/api/v1/categories").json() == []


# ---------- Product creation ----------


def test_product_numbers_are_sequential_and_sku_defaults_to_number(client, admin, category):
    first = create_product(client, admin, category)
    second = create_product(client, admin, category, name="Steel Water Bottle")
    assert first["product_number"].startswith("P-")
    n1, n2 = int(first["product_number"][2:]), int(second["product_number"][2:])
    assert n2 == n1 + 1
    assert first["sku"]["sku"] == first["product_number"]
    assert first["sku"]["currency"] == "INR"
    assert first["status"] == "DRAFT"
    assert second["slug"] == "steel-water-bottle-2"


def test_product_number_cannot_be_changed(client, admin, category):
    product = create_product(client, admin, category)
    resp = client.patch(
        f"/api/v1/admin/products/{product['id']}",
        json={"product_number": "P-999999", "name": "Renamed"},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.json()["product_number"] == product["product_number"]
    assert resp.json()["name"] == "Renamed"


def test_duplicate_sku_rejected(client, admin, category):
    create_product(client, admin, category, sku="BOTTLE-1")
    resp = client.post(
        "/api/v1/admin/products",
        json={
            "name": "Other",
            "category_id": category["id"],
            "price_minor": 100,
            "sku": "BOTTLE-1",
        },
        headers=admin,
    )
    assert resp.status_code == 409


def test_compare_at_must_exceed_price(client, admin, category):
    resp = client.post(
        "/api/v1/admin/products",
        json={
            "name": "X",
            "category_id": category["id"],
            "price_minor": 1000,
            "compare_at_minor": 900,
        },
        headers=admin,
    )
    assert resp.status_code == 422
    product = create_product(client, admin, category, compare_at_minor=60000)
    resp = client.patch(
        f"/api/v1/admin/products/{product['id']}", json={"price_minor": 70000}, headers=admin
    )
    assert resp.status_code == 400


def test_negative_stock_and_price_rejected(client, admin, category):
    for field in ("price_minor", "stock_qty"):
        resp = client.post(
            "/api/v1/admin/products",
            json={"name": "X", "category_id": category["id"], "price_minor": 100, field: -1},
            headers=admin,
        )
        assert resp.status_code == 422


# ---------- Media ----------


def test_first_image_becomes_primary_and_is_stored(client, admin, category, storage):
    product = create_product(client, admin, category)
    resp = upload(client, admin, product["id"])
    assert resp.status_code == 201, resp.text
    media = resp.json()["media"]
    assert len(media) == 1
    assert media[0]["is_primary"] is True
    assert media[0]["width"] == 40
    assert media[0]["url"].startswith("https://cdn.test/products/")
    assert len(storage.objects) == 1

    second = upload(client, admin, product["id"], png_bytes("green")).json()["media"]
    assert [m["is_primary"] for m in second] == [True, False]


def test_fake_image_rejected_even_with_image_name_and_type(client, admin, category, storage):
    product = create_product(client, admin, category)
    resp = upload(client, admin, product["id"], b"<script>alert(1)</script>", "evil.png")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_image"
    assert storage.objects == {}


def test_unsupported_image_format_rejected(client, admin, category):
    product = create_product(client, admin, category)
    buf = io.BytesIO()
    Image.new("RGB", (5, 5)).save(buf, "GIF")
    resp = upload(client, admin, product["id"], buf.getvalue(), "a.gif", "image/gif")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unsupported_image"


def test_exif_metadata_is_stripped(client, admin, category, storage):
    product = create_product(client, admin, category)
    assert (
        upload(client, admin, product["id"], jpeg_with_exif(), "a.jpg", "image/jpeg").status_code
        == 201
    )
    ((data, content_type),) = storage.objects.values()
    assert content_type == "image/jpeg"
    assert b"SecretCameraMaker" not in data


def test_deleting_primary_promotes_next_image(client, admin, category, storage):
    product = create_product(client, admin, category)
    upload(client, admin, product["id"])
    media = upload(client, admin, product["id"], png_bytes("green")).json()["media"]
    resp = client.delete(
        f"/api/v1/admin/products/{product['id']}/media/{media[0]['id']}", headers=admin
    )
    assert resp.status_code == 200
    remaining = resp.json()["media"]
    assert len(remaining) == 1 and remaining[0]["is_primary"] is True
    assert len(storage.objects) == 1


# ---------- Publishing ----------


def test_cannot_publish_without_image(client, admin, category):
    product = create_product(client, admin, category)
    resp = publish(client, admin, product["id"])
    assert resp.status_code == 422
    assert "no primary image" in resp.json()["error"]["message"]


def test_publish_makes_product_public_and_unpublish_hides_it(client, admin, category):
    product = create_product(client, admin, category)
    assert client.get(f"/api/v1/products/{product['slug']}").status_code == 404
    upload(client, admin, product["id"])
    resp = publish(client, admin, product["id"])
    assert resp.status_code == 200
    assert resp.json()["published_at"] is not None

    detail = client.get(f"/api/v1/products/{product['slug']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["availability"] == "IN_STOCK"
    assert body["attributes"] == [{"name": "Capacity", "value": "1 L"}]
    assert body["image_alt"] == "Bottle front"

    client.post(f"/api/v1/admin/products/{product['id']}/unpublish", headers=admin)
    assert client.get(f"/api/v1/products/{product['slug']}").status_code == 404


def test_published_product_is_found_by_its_number(client, admin, category):
    product = create_product(client, admin, category)
    number = product["product_number"]
    assert client.get(f"/api/v1/products/by-number/{number}").status_code == 404
    upload(client, admin, product["id"])
    publish(client, admin, product["id"])

    body = client.get(f"/api/v1/products/by-number/{number}").json()
    assert body["product_number"] == number
    assert body["slug"] == product["slug"]
    # Lower case works too, and a renamed product keeps its number.
    client.patch(f"/api/v1/admin/products/{product['id']}", json={"name": "Renamed"}, headers=admin)
    again = client.get(f"/api/v1/products/by-number/{number.lower()}")
    assert again.status_code == 200
    assert again.json()["name"] == "Renamed"
    assert client.get("/api/v1/products/by-number/P-999999").status_code == 404


def test_archived_product_cannot_be_republished_or_edited(client, admin, category):
    product = create_product(client, admin, category)
    upload(client, admin, product["id"])
    client.post(f"/api/v1/admin/products/{product['id']}/archive", headers=admin)
    assert publish(client, admin, product["id"]).status_code == 400
    resp = client.patch(
        f"/api/v1/admin/products/{product['id']}", json={"name": "Y"}, headers=admin
    )
    assert resp.status_code == 400


def test_manager_cannot_create_or_publish(client, staff_token, admin, category):
    manager = {"Authorization": f"Bearer {staff_token('Manager')}"}
    product = create_product(client, admin, category)
    upload(client, admin, product["id"])
    assert publish(client, manager, product["id"]).status_code == 403
    assert client.get("/api/v1/admin/products", headers=manager).status_code == 200


def test_product_changes_are_audited(client, admin, category):
    product = create_product(client, admin, category)
    upload(client, admin, product["id"])
    publish(client, admin, product["id"])
    client.patch(f"/api/v1/admin/products/{product['id']}", json={"price_minor": 1}, headers=admin)

    from sqlalchemy import select

    from app.infrastructure.database import SessionLocal
    from app.modules.audit.models import AuditLog

    with SessionLocal() as db:
        logs = db.scalars(select(AuditLog).where(AuditLog.entity_id == product["id"])).all()
    actions = [log.action for log in logs]
    assert {"products.created", "products.published", "products.updated"} <= set(actions)
    update = next(log for log in logs if log.action == "products.updated")
    assert update.before["price_minor"] == 49900 and update.after["price_minor"] == 1


# ---------- Public catalogue ----------


def make_published(client, admin, category, name, price, stock=10):
    product = create_product(client, admin, category, name=name, price_minor=price, stock_qty=stock)
    upload(client, admin, product["id"])
    assert publish(client, admin, product["id"]).status_code == 200
    return product


def test_listing_shows_only_published_and_supports_search_sort_and_paging(client, admin, category):
    make_published(client, admin, category, "Blue Mug", 30000)
    make_published(client, admin, category, "Red Mug", 10000, stock=2)
    make_published(client, admin, category, "Green Plate", 20000, stock=0)
    create_product(client, admin, category, name="Draft Mug")

    listing = client.get("/api/v1/products?sort=price_asc").json()
    assert [p["name"] for p in listing["items"]] == ["Red Mug", "Green Plate", "Blue Mug"]
    assert [p["availability"] for p in listing["items"]] == [
        "LOW_STOCK",
        "OUT_OF_STOCK",
        "IN_STOCK",
    ]

    mugs = client.get("/api/v1/products?q=mug&sort=name").json()
    assert [p["name"] for p in mugs["items"]] == ["Blue Mug", "Red Mug"]

    page2 = client.get("/api/v1/products?sort=price_desc&page=2&page_size=2").json()
    assert page2["total"] == 3
    assert [p["name"] for p in page2["items"]] == ["Red Mug"]


def test_category_filter_includes_subcategories(client, admin, category):
    child = client.post(
        "/api/v1/admin/categories",
        json={"name": "Bottles", "parent_id": category["id"]},
        headers=admin,
    ).json()
    other = client.post("/api/v1/admin/categories", json={"name": "Toys"}, headers=admin).json()
    make_published(client, admin, child, "Flask", 1000)
    make_published(client, admin, other, "Ball", 1000)

    names = [
        p["name"] for p in client.get("/api/v1/products?category=home-kitchen").json()["items"]
    ]
    assert names == ["Flask"]
    assert client.get("/api/v1/products?category=missing").json()["total"] == 0


def test_public_payload_does_not_leak_admin_fields(client, admin, category):
    product = make_published(client, admin, category, "Mug", 1000)
    body = client.get(f"/api/v1/products/{product['slug']}").json()
    for field in ("stock_qty", "created_by", "updated_by", "status", "id"):
        assert field not in body

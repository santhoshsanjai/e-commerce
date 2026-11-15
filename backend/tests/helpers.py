"""Small builders shared by API tests."""

import io
import uuid

from PIL import Image


def png_bytes(color: str = "red", size: tuple[int, int] = (40, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def published_product(client, admin_headers, *, name="Mug", price=10000, stock=10, category=None):
    """Create a category (if needed) and a published product; returns the admin product JSON."""
    if category is None:
        category = client.post(
            "/api/v1/admin/categories", json={"name": f"Cat {name}"}, headers=admin_headers
        ).json()
    product = client.post(
        "/api/v1/admin/products",
        json={
            "name": name,
            "category_id": category["id"],
            "price_minor": price,
            "stock_qty": stock,
        },
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/admin/products/{product['id']}/media",
        files={"file": ("p.png", png_bytes(), "image/png")},
        headers=admin_headers,
    )
    resp = client.post(f"/api/v1/admin/products/{product['id']}/publish", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


ADDRESS = {
    "recipient_name": "Asha Rao",
    "phone": "+91 98765 43210",
    "line1": "12 MG Road",
    "line2": "Flat 4B",
    "landmark": "Near the metro",
    "city": "Bengaluru",
    "region": "Karnataka",
    "postal_code": "560001",
}


def place_order(client, buyer_token, admin, *, name="Asha", address=None, qty=1, price=49950):
    h = auth(buyer_token(name))
    addr = client.post("/api/v1/me/addresses", json=address or ADDRESS, headers=h).json()
    product = published_product(client, admin, name=f"Bottle {uuid.uuid4().hex[:6]}", price=price)
    client.post("/api/v1/cart/items", json={"sku_id": product["sku"]["id"], "qty": qty}, headers=h)
    resp = client.post(
        "/api/v1/checkout",
        json={"address_id": addr["id"], "delivery_instructions": "Call first"},
        headers={**h, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert resp.status_code == 201, resp.text
    return resp.json(), h


def admin_id(client, admin, order_number):
    items = client.get("/api/v1/admin/orders", params={"q": order_number}, headers=admin).json()
    return items["items"][0]["id"]

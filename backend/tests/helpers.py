"""Small builders shared by API tests."""

import io

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

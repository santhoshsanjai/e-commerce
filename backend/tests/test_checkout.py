import threading
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.helpers import ADDRESS, auth, published_product


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


@pytest.fixture
def buyer(client, buyer_token):
    h = auth(buyer_token("Asha"))
    address = client.post("/api/v1/me/addresses", json=ADDRESS, headers=h).json()
    return {"headers": h, "address_id": address["id"]}


def add(client, buyer, product, qty=1):
    return client.post(
        "/api/v1/cart/items",
        json={"sku_id": product["sku"]["id"], "qty": qty},
        headers=buyer["headers"],
    )


def checkout(client, buyer, key=None, **extra):
    return client.post(
        "/api/v1/checkout",
        json={"address_id": buyer["address_id"], "payment_method": "COD", **extra},
        headers={**buyer["headers"], "Idempotency-Key": key or uuid.uuid4().hex},
    )


def stock_of(client, admin, product):
    return client.get(f"/api/v1/admin/products/{product['id']}", headers=admin).json()["sku"][
        "stock_qty"
    ]


# ---------- Cart ----------


def test_cart_add_merge_update_remove(client, admin, buyer):
    mug = published_product(client, admin, name="Mug", price=25000, stock=5)
    cart = add(client, buyer, mug, 2).json()
    assert cart["item_count"] == 2
    cart = add(client, buyer, mug, 1).json()
    assert cart["items"][0]["qty"] == 3
    assert cart["subtotal_minor"] == 75000
    assert cart["can_checkout"] is True

    sku = mug["sku"]["id"]
    cart = client.patch(
        f"/api/v1/cart/items/{sku}", json={"qty": 1}, headers=buyer["headers"]
    ).json()
    assert cart["total_minor"] == 25000
    cart = client.delete(f"/api/v1/cart/items/{sku}", headers=buyer["headers"]).json()
    assert cart["items"] == [] and cart["can_checkout"] is False


def test_cannot_add_more_than_stock_or_unpublished(client, admin, buyer):
    mug = published_product(client, admin, stock=2)
    resp = add(client, buyer, mug, 3)
    assert resp.status_code == 409
    assert resp.json()["error"]["details"] == {"max_qty": 2}
    client.post(f"/api/v1/admin/products/{mug['id']}/unpublish", headers=admin)
    assert add(client, buyer, mug, 1).status_code == 404


def test_cart_flags_items_that_became_unavailable(client, admin, buyer):
    mug = published_product(client, admin, stock=5)
    add(client, buyer, mug, 3)
    client.patch(f"/api/v1/admin/products/{mug['id']}", json={"stock_qty": 1}, headers=admin)
    cart = client.get("/api/v1/cart", headers=buyer["headers"]).json()
    assert cart["items"][0]["problem"] == "INSUFFICIENT_STOCK"
    assert cart["can_checkout"] is False


def test_first_cart_requests_at_once_share_one_cart(client, admin, buyer_token):
    """A new buyer's first add-to-cart from two tabs at once: neither request fails."""
    from app.main import app

    mug = published_product(client, admin, stock=10)
    h = auth(buyer_token())
    barrier = threading.Barrier(6)
    results: list[int] = []

    def attempt():
        with TestClient(app) as c:
            barrier.wait()
            results.append(
                c.post(
                    "/api/v1/cart/items", json={"sku_id": mug["sku"]["id"]}, headers=h
                ).status_code
            )

    threads = [threading.Thread(target=attempt) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == [200] * 6
    cart = client.get("/api/v1/cart", headers=h).json()
    assert [i["qty"] for i in cart["items"]] == [6]


def test_cart_requires_buyer_login(client):
    assert client.get("/api/v1/cart").status_code == 401


# ---------- Checkout ----------


def test_checkout_creates_confirmed_cod_order_with_snapshots(client, admin, buyer):
    mug = published_product(client, admin, name="Blue Mug", price=25000, stock=5)
    add(client, buyer, mug, 2)
    resp = checkout(client, buyer, delivery_instructions="Ring twice")
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["order_number"].startswith("ORD-")
    assert order["status"] == "CONFIRMED"
    assert order["payment_method"] == "COD"
    assert order["payment_status"] == "PENDING"
    assert order["total_minor"] == 50000
    assert order["items"] == [
        {
            "id": order["items"][0]["id"],
            "product_number": mug["product_number"],
            "product_name": "Blue Mug",
            "sku": mug["sku"]["sku"],
            "unit_price_minor": 25000,
            "qty": 2,
            "line_total_minor": 50000,
            # Prices include 18% GST by default: 50000 * 18 / 118.
            "gst_rate_bp": 1800,
            "gst_minor": 7627,
        }
    ]
    assert order["shipping_address"]["postal_code"] == "560001"
    assert order["delivery_instructions"] == "Ring twice"
    assert [e["to_status"] for e in order["timeline"]] == ["CONFIRMED"]

    assert stock_of(client, admin, mug) == 3
    assert client.get("/api/v1/cart", headers=buyer["headers"]).json()["items"] == []


def test_order_snapshot_does_not_change_when_product_is_edited(client, admin, buyer):
    mug = published_product(client, admin, name="Blue Mug", price=25000)
    add(client, buyer, mug)
    order = checkout(client, buyer).json()
    client.patch(
        f"/api/v1/admin/products/{mug['id']}",
        json={"name": "Renamed Mug", "price_minor": 99900},
        headers=admin,
    )
    again = client.get(
        f"/api/v1/me/orders/{order['order_number']}", headers=buyer["headers"]
    ).json()
    assert again["items"][0]["product_name"] == "Blue Mug"
    assert again["items"][0]["unit_price_minor"] == 25000


def test_same_idempotency_key_returns_same_order(client, admin, buyer):
    mug = published_product(client, admin, stock=5)
    add(client, buyer, mug, 1)
    first = checkout(client, buyer, key="retry-key-123")
    second = checkout(client, buyer, key="retry-key-123")
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["order_number"] == second.json()["order_number"]
    assert stock_of(client, admin, mug) == 4
    assert client.get("/api/v1/me/orders", headers=buyer["headers"]).json()["total"] == 1


def test_checkout_requires_idempotency_key(client, buyer):
    resp = client.post(
        "/api/v1/checkout", json={"address_id": buyer["address_id"]}, headers=buyer["headers"]
    )
    assert resp.status_code == 422


def test_checkout_rejects_empty_cart_and_foreign_address(client, admin, buyer, buyer_token):
    assert checkout(client, buyer).json()["error"]["code"] == "cart_empty"
    other = auth(buyer_token())
    foreign = client.post("/api/v1/me/addresses", json=ADDRESS, headers=other).json()
    mug = published_product(client, admin)
    add(client, buyer, mug)
    resp = checkout(client, {**buyer, "address_id": foreign["id"]})
    assert resp.status_code == 404


def test_checkout_rechecks_stock_and_publication(client, admin, buyer):
    mug = published_product(client, admin, name="Mug", stock=5)
    add(client, buyer, mug, 2)
    client.patch(f"/api/v1/admin/products/{mug['id']}", json={"stock_qty": 1}, headers=admin)
    resp = checkout(client, buyer)
    assert resp.status_code == 409
    body = resp.json()["error"]
    assert body["code"] == "cart_changed"
    assert body["details"][0]["problem"] == "INSUFFICIENT_STOCK"
    assert stock_of(client, admin, mug) == 1

    client.patch(f"/api/v1/admin/products/{mug['id']}", json={"stock_qty": 5}, headers=admin)
    client.post(f"/api/v1/admin/products/{mug['id']}/unpublish", headers=admin)
    assert checkout(client, buyer).json()["error"]["details"][0]["problem"] == "UNAVAILABLE"


def test_two_buyers_racing_for_the_last_unit_only_one_wins(client, admin, buyer_token):
    """Handoff section 12: concurrency test for the last item in stock."""
    from app.main import app

    mug = published_product(client, admin, stock=1)
    buyers = []
    for _ in range(2):
        h = auth(buyer_token())
        address = client.post("/api/v1/me/addresses", json=ADDRESS, headers=h).json()
        client.post("/api/v1/cart/items", json={"sku_id": mug["sku"]["id"]}, headers=h)
        buyers.append({"headers": h, "address_id": address["id"]})

    barrier = threading.Barrier(2)
    results: list[int] = []

    def attempt(b):
        with TestClient(app) as c:
            barrier.wait()
            results.append(checkout(c, b).status_code)

    threads = [threading.Thread(target=attempt, args=(b,)) for b in buyers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == [201, 409]
    assert stock_of(client, admin, mug) == 0


# ---------- Orders ----------


def test_buyer_sees_only_own_orders(client, admin, buyer, buyer_token):
    mug = published_product(client, admin)
    add(client, buyer, mug)
    order = checkout(client, buyer).json()
    other = auth(buyer_token())
    assert client.get("/api/v1/me/orders", headers=other).json()["total"] == 0
    resp = client.get(f"/api/v1/me/orders/{order['order_number']}", headers=other)
    assert resp.status_code == 404


def test_admin_order_search(client, admin, buyer, staff_token):
    mug = published_product(client, admin, name="Mug")
    plate = published_product(client, admin, name="Plate")
    add(client, buyer, mug)
    first = checkout(client, buyer).json()
    add(client, buyer, plate)
    second = checkout(client, buyer).json()

    manager = auth(staff_token("Manager"))

    def search(**params):
        resp = client.get("/api/v1/admin/orders", params=params, headers=manager)
        assert resp.status_code == 200, resp.text
        return [o["order_number"] for o in resp.json()["items"]]

    assert search() == [second["order_number"], first["order_number"]]
    assert search(q=first["order_number"]) == [first["order_number"]]
    assert search(q=plate["product_number"]) == [second["order_number"]]
    assert search(q="98765") == [second["order_number"], first["order_number"]]
    assert search(q="Asha") != []
    assert search(status="CANCELLED") == []

    order_id = client.get("/api/v1/admin/orders", headers=manager).json()["items"][0]["id"]
    detail = client.get(f"/api/v1/admin/orders/{order_id}", headers=manager).json()
    assert detail["customer_email"].endswith("@example.com")
    assert detail["shipping_address"]["city"] == "Bengaluru"

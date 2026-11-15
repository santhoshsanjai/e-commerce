import pytest

from tests.helpers import admin_id, auth, place_order, published_product


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def dash(client, headers):
    resp = client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_empty_shop(client, admin):
    d = dash(client, admin)
    assert d["today"]["orders"] == 0
    assert len(d["last_7_days"]) == 7
    assert d["attention"]["awaiting_dispatch"] == 0
    assert d["status_counts"]["CONFIRMED"] == 0


def test_counts_sales_and_attention(client, buyer_token, admin):
    o1, _ = place_order(client, buyer_token, admin, qty=2, price=10000)
    o2, _ = place_order(client, buyer_token, admin, name="Ravi", price=5000)
    o3, _ = place_order(client, buyer_token, admin, name="Meena", price=7000)
    id2 = admin_id(client, admin, o2["order_number"])
    id3 = admin_id(client, admin, o3["order_number"])
    client.post("/api/v1/admin/dispatch-batches", json={"order_ids": [id2]}, headers=admin)
    client.post(
        f"/api/v1/admin/orders/{id3}/status",
        json={"status": "CANCELLED", "reason": "Buyer changed mind"},
        headers=admin,
    )

    d = dash(client, admin)
    # The cancelled order is not a sale.
    assert d["today"]["orders"] == 2
    assert d["today"]["sales_minor"] == o1["total_minor"] + o2["total_minor"]
    assert d["last_7_days"][-1] == d["today"]
    assert d["cod_with_courier_minor"] == o2["total_minor"]
    assert d["attention"]["awaiting_dispatch"] == 1
    assert d["status_counts"]["CANCELLED"] == 1
    assert d["status_counts"]["EXPORTED_TO_COURIER"] == 1


def test_low_stock_lists_published_products(client, admin):
    low = published_product(client, admin, name="Almost gone", stock=2)
    published_product(client, admin, name="Plenty", stock=50)
    items = dash(client, admin)["attention"]["low_stock"]
    assert [i["product_number"] for i in items] == [low["product_number"]]
    assert items[0]["stock_qty"] == 2

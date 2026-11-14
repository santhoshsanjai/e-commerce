import uuid

import pytest

from tests.helpers import admin_id, auth, place_order


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def status_url(oid):
    return f"/api/v1/admin/orders/{oid}/status"


def stock(client, admin, product_number):
    found = client.get("/api/v1/admin/products", params={"q": product_number}, headers=admin)
    return found.json()["items"][0]["stock_qty"]


def new_order(client, buyer_token, admin, qty=1):
    order, buyer = place_order(client, buyer_token, admin, qty=qty)
    return order, buyer, admin_id(client, admin, order["order_number"])


def test_detail_lists_allowed_next_statuses(client, buyer_token, admin):
    _, _, oid = new_order(client, buyer_token, admin)
    detail = client.get(f"/api/v1/admin/orders/{oid}", headers=admin).json()
    assert detail["allowed_next"] == sorted(
        ["READY_FOR_DISPATCH", "EXPORTED_TO_COURIER", "CANCELLED", "ON_HOLD"]
    )
    assert detail["awb_number"] is None


def test_manual_move_follows_lifecycle_and_is_recorded(client, buyer_token, admin):
    order, buyer, oid = new_order(client, buyer_token, admin)
    resp = client.post(status_url(oid), json={"status": "READY_FOR_DISPATCH"}, headers=admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "READY_FOR_DISPATCH"
    event = resp.json()["timeline"][-1]
    assert (event["from_status"], event["source"]) == ("CONFIRMED", "MANUAL")

    mine = client.get(f"/api/v1/me/orders/{order['order_number']}", headers=buyer).json()
    assert mine["status"] == "READY_FOR_DISPATCH"


def test_step_outside_lifecycle_is_refused_without_override(client, buyer_token, admin):
    _, _, oid = new_order(client, buyer_token, admin)
    resp = client.post(status_url(oid), json={"status": "DELIVERED"}, headers=admin)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_transition"
    assert "EXPORTED_TO_COURIER" in resp.json()["error"]["details"]["allowed"]

    same = client.post(status_url(oid), json={"status": "CONFIRMED"}, headers=admin)
    assert same.status_code == 409
    assert same.json()["error"]["code"] == "status_unchanged"


def test_override_needs_permission_and_reason(client, buyer_token, admin, staff_token):
    _, _, oid = new_order(client, buyer_token, admin)
    # Admin role lacks orders.status.override by default.
    denied = client.post(
        status_url(oid),
        json={"status": "DELIVERED", "override": True, "reason": "Courier call"},
        headers=admin,
    )
    assert denied.status_code == 403

    super_admin = auth(staff_token("Super Admin"))
    no_reason = client.post(
        status_url(oid), json={"status": "DELIVERED", "override": True}, headers=super_admin
    )
    assert no_reason.status_code == 422
    ok = client.post(
        status_url(oid),
        json={"status": "DELIVERED", "override": True, "reason": "Courier confirmed by phone"},
        headers=super_admin,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "DELIVERED"
    assert ok.json()["payment_status"] == "PAID"
    assert ok.json()["timeline"][-1]["reason"] == "Courier confirmed by phone"


def test_cancel_before_handover_restocks_and_needs_reason(client, buyer_token, admin):
    order, _, oid = new_order(client, buyer_token, admin, qty=3)
    product_number = order["items"][0]["product_number"]
    before = stock(client, admin, product_number)

    assert (
        client.post(status_url(oid), json={"status": "CANCELLED"}, headers=admin).status_code == 422
    )
    resp = client.post(
        status_url(oid),
        json={"status": "CANCELLED", "reason": "Buyer called to cancel"},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    assert stock(client, admin, product_number) == before + 3


def test_cancel_after_handover_does_not_restock(client, buyer_token, admin):
    order, _, oid = new_order(client, buyer_token, admin, qty=2)
    product_number = order["items"][0]["product_number"]
    client.post("/api/v1/admin/dispatch-batches", json={"order_ids": [oid]}, headers=admin)
    before = stock(client, admin, product_number)
    resp = client.post(
        status_url(oid), json={"status": "CANCELLED", "reason": "Lost by courier"}, headers=admin
    )
    assert resp.status_code == 200, resp.text
    assert stock(client, admin, product_number) == before


def test_delivered_cod_is_paid_then_completed(client, buyer_token, admin):
    _, _, oid = new_order(client, buyer_token, admin)
    client.post("/api/v1/admin/dispatch-batches", json={"order_ids": [oid]}, headers=admin)
    delivered = client.post(status_url(oid), json={"status": "DELIVERED"}, headers=admin).json()
    assert (delivered["status"], delivered["payment_status"]) == ("DELIVERED", "PAID")
    done = client.post(status_url(oid), json={"status": "COMPLETED"}, headers=admin).json()
    assert done["status"] == "COMPLETED"
    assert done["allowed_next"] == []


def test_unknown_order_is_404(client, admin):
    resp = client.post(status_url(uuid.uuid4()), json={"status": "CANCELLED"}, headers=admin)
    assert resp.status_code == 404

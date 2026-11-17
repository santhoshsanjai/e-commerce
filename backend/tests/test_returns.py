from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.infrastructure.database import SessionLocal
from app.modules.orders.models import OrderStatusEvent
from tests.helpers import admin_id, auth, place_order

RETURNS = "/api/v1/admin/returns"


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def delivered(client, buyer_token, admin, qty=2):
    order, buyer = place_order(client, buyer_token, admin, qty=qty, price=50000)
    oid = admin_id(client, admin, order["order_number"])
    client.post("/api/v1/admin/dispatch-batches", json={"order_ids": [oid]}, headers=admin)
    resp = client.post(
        f"/api/v1/admin/orders/{oid}/status", json={"status": "DELIVERED"}, headers=admin
    )
    assert resp.status_code == 200, resp.text
    return order, buyer, oid


def ask(client, buyer, order, qty=1, reason="DAMAGED", note="Cracked lid"):
    item = order["items"][0]
    return client.post(
        f"/api/v1/me/orders/{order['order_number']}/return",
        json={"items": [{"order_item_id": item["id"], "qty": qty}], "reason": reason, "note": note},
        headers=buyer,
    )


def stock_of(client, admin, product_number):
    found = client.get("/api/v1/admin/products", params={"q": product_number}, headers=admin)
    return found.json()["items"][0]["stock_qty"]


def test_full_return_journey_restocks_refunds_and_emails(client, buyer_token, admin, outbox):
    order, buyer, _ = delivered(client, buyer_token, admin)
    n = order["order_number"]
    product_number = order["items"][0]["product_number"]
    start_stock = stock_of(client, admin, product_number)

    status = client.get(f"/api/v1/me/orders/{n}/return", headers=buyer).json()
    assert status["can_request"] is True and status["current"] is None
    assert status["deadline"] is not None

    asked = ask(client, buyer, order, qty=2)
    assert asked.status_code == 201, asked.text
    ret = asked.json()
    assert ret["status"] == "REQUESTED" and ret["return_number"].startswith("RET-")
    assert ret["items_value_minor"] == 100000
    # Only one open return per order.
    assert ask(client, buyer, order).status_code == 409

    listed = client.get(RETURNS, params={"status": "REQUESTED"}, headers=admin).json()
    rid = listed["items"][0]["id"]
    assert listed["items"][0]["customer_name"].startswith("Asha")

    approved = client.post(
        f"{RETURNS}/{rid}/approve", json={"note": "Courier picks up Monday"}, headers=admin
    )
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    # Refund needs a paid order: the COD order was paid on delivery.
    received = client.post(
        f"{RETURNS}/{rid}/receive",
        json={"restock": [order["items"][0]["id"]]},
        headers=admin,
    )
    assert received.json()["status"] == "RECEIVED"
    assert received.json()["items"][0]["restocked"] is True
    assert stock_of(client, admin, product_number) == start_stock + 2

    too_much = client.post(
        f"{RETURNS}/{rid}/refund", json={"amount_minor": 10**9, "method": "UPI"}, headers=admin
    )
    assert too_much.status_code == 422
    refunded = client.post(
        f"{RETURNS}/{rid}/refund",
        json={"amount_minor": order["total_minor"], "method": "UPI", "reference": "UTR123"},
        headers=admin,
    )
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["status"] == "REFUNDED"
    assert refunded.json()["payment_status"] == "REFUNDED"

    mine = client.get(f"/api/v1/me/orders/{n}/return", headers=buyer).json()
    assert mine["current"]["status"] == "REFUNDED" and mine["can_request"] is False

    subjects = [e.subject.split(" · ")[0] for e in outbox.sent]
    rn = ret["return_number"]
    assert subjects[-3:] == [
        f"Return {rn} requested",
        f"Return {rn} approved",
        f"Refund for return {rn}",
    ]
    assert "Courier picks up Monday" in outbox.sent[-2].text
    assert "UTR123" in outbox.sent[-1].text

    actions = client.get("/api/v1/admin/audit-logs", params={"q": rid}, headers=admin).json()
    assert {a["action"] for a in actions["items"]} >= {
        "returns.approved",
        "returns.received",
        "returns.refunded",
    }


def test_returns_open_only_after_delivery_and_within_the_window(client, buyer_token, admin):
    order, buyer = place_order(client, buyer_token, admin)
    resp = ask(client, buyer, order)
    assert resp.status_code == 409 and "delivered" in resp.json()["error"]["message"]

    order, buyer, _ = delivered(client, buyer_token, admin)
    with SessionLocal() as db:
        db.execute(
            update(OrderStatusEvent)
            .where(OrderStatusEvent.to_status == "DELIVERED")
            .values(occurred_at=datetime.now(UTC) - timedelta(days=8))
        )
        db.commit()
    status = client.get(f"/api/v1/me/orders/{order['order_number']}/return", headers=buyer).json()
    assert status["can_request"] is False and "closed" in status["reason_not"]
    assert ask(client, buyer, order).status_code == 409


def test_items_must_come_from_the_order_and_within_its_quantity(client, buyer_token, admin):
    order, buyer, _ = delivered(client, buyer_token, admin, qty=1)
    assert ask(client, buyer, order, qty=2).status_code == 400
    other, _ = place_order(client, buyer_token, admin)
    foreign = client.post(
        f"/api/v1/me/orders/{order['order_number']}/return",
        json={"items": [{"order_item_id": other["items"][0]["id"], "qty": 1}], "reason": "OTHER"},
        headers=buyer,
    )
    assert foreign.status_code == 400


def test_another_buyer_cannot_see_or_return_my_order(client, buyer_token, admin):
    order, _, _ = delivered(client, buyer_token, admin)
    stranger = auth(buyer_token("Stranger"))
    assert (
        client.get(
            f"/api/v1/me/orders/{order['order_number']}/return", headers=stranger
        ).status_code
        == 404
    )
    assert ask(client, stranger, order).status_code == 404


def test_rejecting_needs_a_reason_and_frees_the_order_for_a_new_request(
    client, buyer_token, admin, outbox
):
    order, buyer, _ = delivered(client, buyer_token, admin)
    ask(client, buyer, order)
    rid = client.get(RETURNS, headers=admin).json()["items"][0]["id"]
    assert (
        client.post(f"{RETURNS}/{rid}/reject", json={"note": ""}, headers=admin).status_code == 422
    )
    resp = client.post(
        f"{RETURNS}/{rid}/reject", json={"note": "Used items can't be returned"}, headers=admin
    )
    assert resp.json()["status"] == "REJECTED"
    assert "Used items can't be returned" in outbox.sent[-1].text
    # Steps out of order are refused.
    assert client.post(f"{RETURNS}/{rid}/receive", json={}, headers=admin).status_code == 409
    # A new request is possible after a rejection.
    assert ask(client, buyer, order, reason="WRONG_ITEM").status_code == 201


def test_buyer_can_withdraw_before_a_decision(client, buyer_token, admin):
    order, buyer, _ = delivered(client, buyer_token, admin)
    rn = ask(client, buyer, order).json()["return_number"]
    resp = client.post(f"/api/v1/me/returns/{rn}/withdraw", headers=buyer)
    assert resp.status_code == 200 and resp.json()["status"] == "WITHDRAWN"
    assert client.post(f"/api/v1/me/returns/{rn}/withdraw", headers=buyer).status_code == 409


def test_manager_can_view_but_not_decide(client, buyer_token, admin, staff_token):
    order, buyer, _ = delivered(client, buyer_token, admin)
    ask(client, buyer, order)
    manager = auth(staff_token("Manager"))
    rid = client.get(RETURNS, headers=manager).json()["items"][0]["id"]
    assert client.post(f"{RETURNS}/{rid}/approve", json={}, headers=manager).status_code == 403


def test_buyer_can_cancel_before_handover_and_stock_returns(client, buyer_token, admin, outbox):
    order, buyer = place_order(client, buyer_token, admin, qty=2)
    product_number = order["items"][0]["product_number"]
    before = stock_of(client, admin, product_number)
    assert order["can_cancel"] is True
    resp = client.post(
        f"/api/v1/me/orders/{order['order_number']}/cancel",
        json={"reason": "Ordered twice"},
        headers=buyer,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CANCELLED" and resp.json()["can_cancel"] is False
    assert resp.json()["timeline"][-1]["source"] == "BUYER"
    assert stock_of(client, admin, product_number) == before + 2
    assert outbox.sent[-1].subject.startswith(f"Order {order['order_number']} cancelled")

    shipped, buyer2, _ = delivered(client, buyer_token, admin)
    late = client.post(
        f"/api/v1/me/orders/{shipped['order_number']}/cancel", json={}, headers=buyer2
    )
    assert late.status_code == 409 and late.json()["error"]["code"] == "cannot_cancel"

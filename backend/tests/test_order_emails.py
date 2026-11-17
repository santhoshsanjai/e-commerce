from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.infrastructure.database import SessionLocal
from app.modules.notifications.models import EmailOutbox
from app.modules.notifications.service import deliver_pending, purge_sent, rupees
from tests.helpers import admin_id, auth, place_order
from tests.test_courier_import import upload, xlsx


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def subjects(outbox):
    return [e.subject.split(" · ")[0] for e in outbox.sent]


def status(client, admin, oid, target, reason=""):
    resp = client.post(
        f"/api/v1/admin/orders/{oid}/status",
        json={"status": target, "reason": reason},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text


def test_rupees_uses_indian_grouping():
    assert rupees(0) == "₹0"
    assert rupees(49950) == "₹499.50"
    assert rupees(12345678_00) == "₹1,23,45,678"


def test_checkout_sends_a_confirmation_with_items_total_and_address(
    client, buyer_token, admin, outbox
):
    order, _ = place_order(client, buyer_token, admin, name="Asha")
    assert subjects(outbox) == [f"Order {order['order_number']} confirmed"]
    email = outbox.sent[0]
    assert email.to.endswith("@example.com")
    assert "1 x Bottle" in email.text
    assert "Total: ₹499.50" in email.text
    assert "keep ₹499.50 ready to pay in cash" in email.text
    assert f"/orders/{order['order_number']}" in email.text


def test_a_checkout_queues_exactly_one_email(client, buyer_token, admin, outbox):
    place_order(client, buyer_token, admin)
    with SessionLocal() as db:
        assert len(db.scalars(select(EmailOutbox)).all()) == 1
    assert len(outbox.sent) == 1


def test_status_changes_email_the_buyer_at_the_moments_that_matter(
    client, buyer_token, admin, outbox
):
    order, _ = place_order(client, buyer_token, admin)
    n = order["order_number"]
    oid = admin_id(client, admin, n)
    client.post("/api/v1/admin/dispatch-batches", json={"order_ids": [oid]}, headers=admin)
    upload_id = upload(client, admin, xlsx([(n, "AWB777", "In Transit", None)])).json()["id"]
    client.post(f"/api/v1/admin/courier-imports/{upload_id}/confirm", headers=admin)
    status(client, admin, oid, "OUT_FOR_DELIVERY")
    status(client, admin, oid, "DELIVERED")
    status(client, admin, oid, "COMPLETED")

    assert subjects(outbox) == [
        f"Order {n} confirmed",
        f"Order {n} has shipped",
        f"Order {n} is out for delivery",
        f"Order {n} delivered",
    ]
    assert "AWB777" in outbox.sent[1].text


def test_cancelling_emails_the_buyer(client, buyer_token, admin, outbox):
    order, _ = place_order(client, buyer_token, admin)
    oid = admin_id(client, admin, order["order_number"])
    status(client, admin, oid, "CANCELLED", reason="Customer asked")
    assert subjects(outbox)[-1] == f"Order {order['order_number']} cancelled"
    assert "Customer asked" not in outbox.sent[-1].text  # staff notes stay internal


def test_a_failed_send_is_retried_later_and_never_breaks_the_request(
    client, buyer_token, admin, outbox
):
    class Broken:
        def send(self, email):
            raise ConnectionError("smtp down")

    from app.infrastructure.email import get_email_sender
    from app.main import app

    app.dependency_overrides[get_email_sender] = lambda: Broken()
    order, _ = place_order(client, buyer_token, admin)
    assert order["status"] == "CONFIRMED"
    with SessionLocal() as db:
        row = db.scalars(select(EmailOutbox)).one()
        assert (row.sent_at, row.attempts) == (None, 1)
        assert "smtp down" in row.last_error
        assert row.next_attempt_at > datetime.now(UTC)
        # The retry time arrives.
        db.execute(update(EmailOutbox).values(next_attempt_at=datetime.now(UTC)))
        db.commit()

    assert deliver_pending(outbox) == 1
    assert deliver_pending(outbox) == 0  # sent once only
    assert subjects(outbox) == [f"Order {order['order_number']} confirmed"]


def test_old_sent_emails_are_purged(client, buyer_token, admin, outbox):
    place_order(client, buyer_token, admin)
    with SessionLocal() as db:
        assert purge_sent(db) == 0
        assert purge_sent(db, now=datetime.now(UTC) + timedelta(days=31)) == 1
        assert db.scalars(select(EmailOutbox)).all() == []

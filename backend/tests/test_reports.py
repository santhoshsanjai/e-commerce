import io
from datetime import UTC, datetime

import pytest
from openpyxl import load_workbook
from sqlalchemy import select, update

from tests.helpers import ADDRESS, admin_id, auth, place_order

URL = "/api/v1/admin/reports/sales"


@pytest.fixture
def boss(staff_token):
    return auth(staff_token("Super Admin"))


def _place_at(order_number: str, when: datetime) -> None:
    from app.infrastructure.database import SessionLocal
    from app.modules.orders.models import Order

    with SessionLocal() as db:
        db.execute(update(Order).where(Order.order_number == order_number).values(placed_at=when))
        db.commit()


def _report(client, headers, **params):
    resp = client.get(URL, params=params, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_default_range_is_last_30_days(client, boss):
    r = _report(client, boss)
    assert len(r["periods"]) == 30
    assert r["summary"]["orders"] == 0
    assert r["summary"]["avg_order_minor"] == 0
    assert r["currency"] == "INR"


def test_summary_counts_sales_cancellations_and_cod(client, buyer_token, boss):
    o1, _ = place_order(client, buyer_token, boss, qty=2, price=10000)
    o2, _ = place_order(client, buyer_token, boss, name="Ravi", price=5000)
    o3, _ = place_order(
        client, buyer_token, boss, name="Meena", price=7000, address={**ADDRESS, "region": "Goa"}
    )
    client.post(
        f"/api/v1/admin/orders/{admin_id(client, boss, o3['order_number'])}/status",
        json={"status": "CANCELLED", "reason": "Out of stock"},
        headers=boss,
    )
    client.post(
        f"/api/v1/admin/orders/{admin_id(client, boss, o2['order_number'])}/status",
        json={"status": "DELIVERED", "reason": "Delivered by hand", "override": True},
        headers=boss,
    )

    s = _report(client, boss)["summary"]
    assert s["orders"] == 2
    assert s["sales_minor"] == o1["total_minor"] + o2["total_minor"]
    assert s["avg_order_minor"] == round(s["sales_minor"] / 2)
    assert s["items_sold"] == 3
    assert (s["delivered_orders"], s["delivered_minor"]) == (1, o2["total_minor"])
    assert s["cod_collected_minor"] == o2["total_minor"]
    assert (s["cancelled_orders"], s["cancelled_minor"]) == (1, o3["total_minor"])
    assert s["returned_orders"] == 0

    r = _report(client, boss)
    assert [g["region"] for g in r["regions"]] == ["Karnataka"]  # cancelled Goa order left out
    assert r["top_products"][0]["qty"] == 2
    assert r["top_products"][0]["sales_minor"] == 20000


def test_days_follow_india_time_and_group_by_week_and_month(client, buyer_token, boss):
    a, _ = place_order(client, buyer_token, boss, price=10000)
    b, _ = place_order(client, buyer_token, boss, name="Ravi", price=20000)
    c, _ = place_order(client, buyer_token, boss, name="Meena", price=30000)
    # 18:45 UTC on 31 Oct is 00:15 on 1 Nov in India.
    _place_at(a["order_number"], datetime(2026, 10, 31, 18, 45, tzinfo=UTC))
    _place_at(b["order_number"], datetime(2026, 11, 3, 6, 0, tzinfo=UTC))
    _place_at(c["order_number"], datetime(2026, 10, 20, 6, 0, tzinfo=UTC))

    days = _report(client, boss, date_from="2026-11-01", date_to="2026-11-07")
    assert days["periods"][0]["orders"] == 1  # order a lands on 1 Nov
    assert days["summary"]["orders"] == 2

    weeks = _report(client, boss, date_from="2026-10-19", date_to="2026-11-08", group_by="week")
    assert [p["start"] for p in weeks["periods"]] == ["2026-10-19", "2026-10-26", "2026-11-02"]
    assert [p["orders"] for p in weeks["periods"]] == [1, 1, 1]
    assert weeks["periods"][0]["label"] == "Week of 19 Oct 2026"

    months = _report(client, boss, date_from="2026-10-01", date_to="2026-11-30", group_by="month")
    assert [(p["label"], p["orders"]) for p in months["periods"]] == [
        ("Oct 2026", 1),
        ("Nov 2026", 2),
    ]
    assert months["periods"][1]["sales_minor"] == a["total_minor"] + b["total_minor"]


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"date_from": "2026-11-10", "date_to": "2026-11-01"}, "invalid_range"),
        ({"date_from": "2025-01-01", "date_to": "2026-11-01"}, "range_too_long"),
    ],
)
def test_bad_ranges(client, boss, params, code):
    resp = client.get(URL, params=params, headers=boss)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == code


def test_excel_export(client, buyer_token, boss):
    o1, _ = place_order(client, buyer_token, boss, name="=HYPERLINK", qty=2, price=10000)
    o2, _ = place_order(client, buyer_token, boss, name="Ravi", price=5000)
    client.post(
        f"/api/v1/admin/orders/{admin_id(client, boss, o2['order_number'])}/status",
        json={"status": "CANCELLED", "reason": "Buyer asked"},
        headers=boss,
    )
    resp = client.get(f"{URL}/export", params={"group_by": "month"}, headers=boss)
    assert resp.status_code == 200
    assert 'attachment; filename="sales-' in resp.headers["content-disposition"]

    wb = load_workbook(io.BytesIO(resp.content))
    assert wb.sheetnames == ["Summary", "By period", "Products", "By state", "Orders"]
    summary = {row[0]: row[1] for row in wb["Summary"].iter_rows(min_row=5, values_only=True)}
    assert summary["Orders"] == 1
    assert summary["Sales"] == o1["total_minor"] / 100
    assert summary["Cancelled orders"] == 1

    orders = list(wb["Orders"].iter_rows(min_row=2, values_only=True))
    assert len(orders) == 2  # every order in the range, cancelled ones included
    statuses = {row[0]: row[2] for row in orders}
    assert statuses[o2["order_number"]] == "Cancelled"
    names = {row[5] for row in orders}
    assert any(n.startswith("'=HYPERLINK") for n in names)  # not run as a formula

    from app.infrastructure.database import SessionLocal
    from app.modules.audit.models import AuditLog

    with SessionLocal() as db:
        actions = set(db.scalars(select(AuditLog.action)).all())
    assert "reports.sales_exported" in actions

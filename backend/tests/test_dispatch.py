import io
import uuid

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app.infrastructure.database import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.dispatch.excel import COLUMNS, safe_text
from tests.helpers import ADDRESS, admin_id, auth, place_order

BATCHES = "/api/v1/admin/dispatch-batches"


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def read_sheet(data: bytes) -> list[list[object]]:
    ws = load_workbook(io.BytesIO(data)).active
    assert ws is not None
    return [list(r) for r in ws.iter_rows(values_only=True)]


def test_create_batch_exports_orders_and_moves_them_to_courier(client, buyer_token, admin, files):
    o1, buyer_h = place_order(client, buyer_token, admin, qty=2)
    o2, _ = place_order(client, buyer_token, admin, name="Ravi")

    eligible = client.get(f"{BATCHES}/eligible-orders", headers=admin).json()
    assert [o["order_number"] for o in eligible] == [o1["order_number"], o2["order_number"]]

    ids = [o["id"] for o in eligible]
    resp = client.post(BATCHES, json={"order_ids": ids}, headers=admin)
    assert resp.status_code == 201, resp.text
    batch = resp.json()
    assert batch["batch_number"].startswith("DSP-")
    assert batch["order_count"] == 2
    assert batch["cod_total_minor"] == o1["total_minor"] + o2["total_minor"]
    assert {o["status"] for o in batch["orders"]} == {"EXPORTED_TO_COURIER"}

    # Nothing left to dispatch, and the buyer sees the new status with a history entry.
    assert client.get(f"{BATCHES}/eligible-orders", headers=admin).json() == []
    mine = client.get(f"/api/v1/me/orders/{o1['order_number']}", headers=buyer_h).json()
    assert mine["status"] == "EXPORTED_TO_COURIER"
    assert mine["timeline"][-1]["reason"] == f"Added to dispatch batch {batch['batch_number']}"

    # The stored file is private and is what the download returns.
    assert len(files.objects) == 1
    download = client.get(f"{BATCHES}/{batch['id']}/file", headers=admin)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert f'filename="{batch["batch_number"]}.xlsx"' in download.headers["content-disposition"]
    assert download.headers["cache-control"] == "no-store"

    rows = read_sheet(download.content)
    assert rows[0] == [c.header for c in COLUMNS]
    first = dict(zip(rows[0], rows[1], strict=True))
    assert first["Order No"] == o1["order_number"]
    assert first["Consignee Name"] == "Asha Rao"
    assert first["Mobile"] == "+91 98765 43210"
    assert first["PIN Code"] == "560001"
    assert first["Quantity"] == 2
    assert first["Payment Mode"] == "COD"
    assert first["COD Amount"] == pytest.approx(o1["total_minor"] / 100)
    assert first["Delivery Instructions"] == "Call first"
    assert first["AWB No"] is None


def test_orders_cannot_join_two_batches(client, buyer_token, admin):
    o1, _ = place_order(client, buyer_token, admin)
    oid = admin_id(client, admin, o1["order_number"])
    assert client.post(BATCHES, json={"order_ids": [oid]}, headers=admin).status_code == 201

    again = client.post(BATCHES, json={"order_ids": [oid]}, headers=admin)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "orders_not_eligible"
    assert again.json()["error"]["details"]["order_numbers"] == [o1["order_number"]]


def test_batch_is_all_or_nothing(client, buyer_token, admin, files):
    o1, _ = place_order(client, buyer_token, admin)
    o2, _ = place_order(client, buyer_token, admin, name="Ravi")
    id1 = admin_id(client, admin, o1["order_number"])
    id2 = admin_id(client, admin, o2["order_number"])
    client.post(BATCHES, json={"order_ids": [id1]}, headers=admin)

    resp = client.post(BATCHES, json={"order_ids": [id2, id1]}, headers=admin)
    assert resp.status_code == 409
    # The eligible order was not touched by the failed attempt.
    eligible = client.get(f"{BATCHES}/eligible-orders", headers=admin).json()
    assert [o["id"] for o in eligible] == [id2]
    assert len(files.objects) == 1


def test_unknown_and_duplicate_ids_are_rejected(client, buyer_token, admin):
    o1, _ = place_order(client, buyer_token, admin)
    oid = admin_id(client, admin, o1["order_number"])
    missing = client.post(BATCHES, json={"order_ids": [str(uuid.uuid4())]}, headers=admin)
    assert missing.status_code == 404
    dup = client.post(BATCHES, json={"order_ids": [oid, oid]}, headers=admin)
    assert dup.status_code == 422
    assert client.post(BATCHES, json={"order_ids": []}, headers=admin).status_code == 422


def test_batch_list_detail_and_audit(client, buyer_token, admin):
    o1, _ = place_order(client, buyer_token, admin)
    oid = admin_id(client, admin, o1["order_number"])
    batch = client.post(BATCHES, json={"order_ids": [oid]}, headers=admin).json()

    page = client.get(BATCHES, headers=admin).json()
    assert page["total"] == 1
    assert page["items"][0]["batch_number"] == batch["batch_number"]
    assert page["items"][0]["created_by_name"]

    detail = client.get(f"{BATCHES}/{batch['id']}", headers=admin).json()
    assert [o["order_number"] for o in detail["orders"]] == [o1["order_number"]]
    assert client.get(f"{BATCHES}/{uuid.uuid4()}", headers=admin).status_code == 404

    client.get(f"{BATCHES}/{batch['id']}/file", headers=admin)
    with SessionLocal() as db:
        actions = db.scalars(select(AuditLog.action).where(AuditLog.entity_id == batch["id"])).all()
    assert sorted(actions) == ["dispatch.batch_created", "dispatch.file_downloaded"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('=HYPERLINK("http://x")', '\'=HYPERLINK("http://x")'),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("-2+3+cmd|' /C calc'!A0", "'-2+3+cmd|' /C calc'!A0"),
        ("+91 98765 43210", "+91 98765 43210"),
        ("12 MG Road", "12 MG Road"),
        (499.5, 499.5),
    ],
)
def test_safe_text_blocks_formulas_but_keeps_phone_numbers(value, expected):
    assert safe_text(value) == expected


def test_formula_like_address_is_neutralised_in_the_file(client, buyer_token, admin):
    evil = {**ADDRESS, "line1": '=HYPERLINK("http://evil.example","click")'}
    o1, _ = place_order(client, buyer_token, admin, address=evil)
    oid = admin_id(client, admin, o1["order_number"])
    batch = client.post(BATCHES, json={"order_ids": [oid]}, headers=admin).json()
    rows = read_sheet(client.get(f"{BATCHES}/{batch['id']}/file", headers=admin).content)
    line1 = rows[1][[c.header for c in COLUMNS].index("Address Line 1")]
    assert isinstance(line1, str) and line1.startswith("'=")

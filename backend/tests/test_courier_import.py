import io
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from openpyxl import Workbook, load_workbook

from app.modules.courier_import.parser import CANONICAL_STATUS_WORDS, STATUS_WORDS
from app.modules.courier_import.parser import _norm as parser_norm
from app.shared.timezones import IST
from tests.helpers import admin_id, auth, place_order

IMPORTS = "/api/v1/admin/courier-imports"


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def xlsx(rows, header=("Order No", "AWB No", "Courier Status", "Status Date")):
    wb = Workbook()
    ws = wb.active
    ws.append(list(header))
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _zip_without_workbook():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("notes.txt", "not a workbook")
    return buf.getvalue()


def upload(client, admin, data, name="courier.xlsx"):
    return client.post(
        IMPORTS,
        files={
            "file": (
                name,
                data,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=admin,
    )


def handed_over(client, buyer_token, admin, name="Asha"):
    order, buyer = place_order(client, buyer_token, admin, name=name)
    oid = admin_id(client, admin, order["order_number"])
    client.post("/api/v1/admin/dispatch-batches", json={"order_ids": [oid]}, headers=admin)
    return order["order_number"], oid, buyer


def test_preview_then_confirm_updates_orders_once(client, buyer_token, admin, files):
    n1, oid1, buyer1 = handed_over(client, buyer_token, admin)
    n2, oid2, _ = handed_over(client, buyer_token, admin, name="Ravi")
    data = xlsx(
        [
            (n1, "AWB111", "Delivered", "01-01-2026 15:30"),
            (n2, "AWB222", "In Transit", None),
            ("ORD-2026-999999", "AWB333", "Delivered", None),
            (n2, "", "Teleported", None),
        ]
    )
    preview = upload(client, admin, data)
    assert preview.status_code == 201, preview.text
    body = preview.json()
    assert body["status"] == "PREVIEW"
    assert body["summary"] == {
        "total": 4,
        "will_update": 2,
        "updated": 0,
        "no_change": 0,
        "error": 2,
    }
    rows = {r["row"]: r for r in body["rows"]}
    assert rows[2]["new_status"] == "DELIVERED" and rows[2]["outcome"] == "will_update"
    assert rows[4]["message"] == "Order not found"
    assert "Unknown courier status" in rows[5]["message"]
    assert any(k.startswith("courier-imports/") for k in files.objects)  # kept privately

    # Nothing changed yet.
    assert client.get(f"/api/v1/admin/orders/{oid1}", headers=admin).json()["status"] == (
        "EXPORTED_TO_COURIER"
    )

    confirmed = client.post(f"{IMPORTS}/{body['id']}/confirm", headers=admin)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"
    assert confirmed.json()["summary"]["updated"] == 2

    o1 = client.get(f"/api/v1/admin/orders/{oid1}", headers=admin).json()
    assert (o1["status"], o1["awb_number"], o1["payment_status"]) == ("DELIVERED", "AWB111", "PAID")
    last = o1["timeline"][-1]
    assert last["source"] == "IMPORT"
    assert last["reason"] == "Courier: Delivered"
    # A courier date before the order existed is pulled forward to the previous step.
    previous = o1["timeline"][-2]
    assert datetime.fromisoformat(last["occurred_at"]) >= datetime.fromisoformat(
        previous["occurred_at"]
    )
    o2 = client.get(f"/api/v1/admin/orders/{oid2}", headers=admin).json()
    assert (o2["status"], o2["awb_number"]) == ("IN_TRANSIT", "AWB222")
    # The buyer sees the tracking number on their order.
    mine = client.get(f"/api/v1/me/orders/{n1}", headers=buyer1).json()
    assert (mine["status"], mine["awb_number"]) == ("DELIVERED", "AWB111")

    # Confirming again changes nothing.
    again = client.post(f"{IMPORTS}/{body['id']}/confirm", headers=admin)
    assert again.status_code == 200
    o1_again = client.get(f"/api/v1/admin/orders/{oid1}", headers=admin).json()
    assert len(o1_again["timeline"]) == len(o1["timeline"])


def test_reuploading_the_same_file_is_a_no_op(client, buyer_token, admin):
    n1, _, _ = handed_over(client, buyer_token, admin)
    data = xlsx([(n1, "AWB111", "Out for delivery", None)])
    first = upload(client, admin, data).json()
    client.post(f"{IMPORTS}/{first['id']}/confirm", headers=admin)

    second = upload(client, admin, data).json()
    assert second["summary"]["no_change"] == 1
    assert second["rows"][0]["message"] == "Already up to date"


def test_older_status_after_newer_is_reported_not_applied(client, buyer_token, admin):
    n1, _, _ = handed_over(client, buyer_token, admin)
    first = upload(client, admin, xlsx([(n1, "AWB1", "Delivered", None)])).json()
    client.post(f"{IMPORTS}/{first['id']}/confirm", headers=admin)
    stale = upload(client, admin, xlsx([(n1, "AWB1", "In transit", None)])).json()
    assert stale["rows"][0]["outcome"] == "no_change"
    assert stale["rows"][0]["message"].startswith("Already further along")


def test_rows_for_one_order_chain_in_file_order(client, buyer_token, admin):
    n1, oid1, _ = handed_over(client, buyer_token, admin)
    data = xlsx([(n1, "AWB1", "Picked up", None), (n1, "AWB1", "Out for delivery", None)])
    preview = upload(client, admin, data).json()
    assert [r["new_status"] for r in preview["rows"]] == ["DISPATCHED", "OUT_FOR_DELIVERY"]
    client.post(f"{IMPORTS}/{preview['id']}/confirm", headers=admin)
    detail = client.get(f"/api/v1/admin/orders/{oid1}", headers=admin).json()
    assert [e["to_status"] for e in detail["timeline"]][-2:] == ["DISPATCHED", "OUT_FOR_DELIVERY"]


def test_order_not_yet_with_courier_is_an_error(client, buyer_token, admin):
    order, _ = place_order(client, buyer_token, admin)
    preview = upload(
        client, admin, xlsx([(order["order_number"], "AWB1", "Delivered", None)])
    ).json()
    assert preview["rows"][0]["outcome"] == "error"
    assert "hasn't been handed to the courier" in preview["rows"][0]["message"]


def test_confirm_rechecks_orders_changed_after_preview(client, buyer_token, admin):
    n1, oid1, _ = handed_over(client, buyer_token, admin)
    preview = upload(client, admin, xlsx([(n1, "AWB1", "Delivered", None)])).json()
    client.post(
        f"/api/v1/admin/orders/{oid1}/status",
        json={"status": "CANCELLED", "reason": "Buyer refused"},
        headers=admin,
    )
    confirmed = client.post(f"{IMPORTS}/{preview['id']}/confirm", headers=admin).json()
    assert confirmed["rows"][0]["outcome"] == "error"
    assert client.get(f"/api/v1/admin/orders/{oid1}", headers=admin).json()["status"] == "CANCELLED"


def test_header_aliases_and_numeric_order_cells(client, buyer_token, admin):
    n1, _, _ = handed_over(client, buyer_token, admin)
    data = xlsx(
        [(n1.lower(), 123456789012, "OFD")], header=("Reference No", "Tracking Number", "Status")
    )
    preview = upload(client, admin, data).json()
    row = preview["rows"][0]
    assert (row["order_number"], row["awb"], row["new_status"]) == (
        n1,
        "123456789012",
        "OUT_FOR_DELIVERY",
    )


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"order,status\n1,delivered", "Excel .xlsx"),
        (_zip_without_workbook(), "couldn't be read"),
    ],
)
def test_unreadable_files_are_rejected(client, admin, data, message):
    resp = upload(client, admin, data)
    assert resp.status_code == 422
    assert message in resp.json()["error"]["message"]


def test_missing_columns_and_empty_sheets_are_rejected(client, admin):
    no_order = upload(client, admin, xlsx([("x",)], header=("Something",)))
    assert no_order.status_code == 422
    assert "order number column" in no_order.json()["error"]["message"]
    empty = upload(client, admin, xlsx([]))
    assert "no data rows" in empty.json()["error"]["message"]


def test_too_large_file_is_rejected(client, admin):
    resp = upload(client, admin, b"0" * (5 * 1024 * 1024 + 1))
    assert resp.status_code == 413


def test_list_and_detail(client, buyer_token, admin):
    n1, _, _ = handed_over(client, buyer_token, admin)
    created = upload(client, admin, xlsx([(n1, "AWB1", "Delivered", None)])).json()
    page = client.get(IMPORTS, headers=admin).json()
    assert page["total"] == 1 and page["items"][0]["uploaded_by_name"]
    detail = client.get(f"{IMPORTS}/{created['id']}", headers=admin).json()
    assert detail["rows"][0]["order_number"] == n1


def test_courier_times_are_read_as_ist_and_never_in_the_future(client, buyer_token, admin):
    n1, oid1, _ = handed_over(client, buyer_token, admin)
    n2, oid2, _ = handed_over(client, buyer_token, admin, name="Ravi")
    soon = (datetime.now(UTC) + timedelta(minutes=10)).astimezone(IST)
    past = (datetime.now(UTC) - timedelta(seconds=1)).astimezone(IST)
    data = xlsx(
        [
            (n1, "A1", "Delivered", soon.strftime("%d-%m-%Y %H:%M")),
            (n2, "A2", "Delivered", past.strftime("%d-%m-%Y %H:%M")),
        ]
    )
    preview = upload(client, admin, data).json()
    client.post(f"{IMPORTS}/{preview['id']}/confirm", headers=admin)
    future = client.get(f"/api/v1/admin/orders/{oid1}", headers=admin).json()["timeline"][-1]
    assert datetime.fromisoformat(future["occurred_at"]) <= datetime.now(UTC)
    exact = client.get(f"/api/v1/admin/orders/{oid2}", headers=admin).json()["timeline"][-1]
    # Read as IST: the minute matches what the courier wrote.
    assert datetime.fromisoformat(exact["occurred_at"]).astimezone(IST).strftime(
        "%H:%M"
    ) == past.strftime("%H:%M")


def test_our_export_round_trips_through_the_import(client, buyer_token, admin):
    """The courier fills the orange columns on our own dispatch sheet and sends it back."""
    n1, oid1, _ = handed_over(client, buyer_token, admin)
    batch = client.get("/api/v1/admin/dispatch-batches", headers=admin).json()["items"][0]
    sheet = client.get(f"/api/v1/admin/dispatch-batches/{batch['id']}/file", headers=admin).content

    wb = load_workbook(io.BytesIO(sheet))
    assert wb.sheetnames == ["Orders", "How to fill"]
    ws = wb["Orders"]
    headers = [c.value for c in ws[1]]
    assert headers[-3:] == ["AWB No", "Courier Status", "Status Date"]
    assert ws.data_validations.dataValidation  # status dropdown offered
    ws.cell(row=2, column=headers.index("AWB No") + 1, value="DTDC12345")
    ws.cell(row=2, column=headers.index("Courier Status") + 1, value="Out For Delivery")
    buf = io.BytesIO()
    wb.save(buf)

    preview = upload(client, admin, buf.getvalue(), name=batch["file_name"]).json()
    assert preview["summary"]["will_update"] == 1, preview["rows"]
    client.post(f"{IMPORTS}/{preview['id']}/confirm", headers=admin)
    order = client.get(f"/api/v1/admin/orders/{oid1}", headers=admin).json()
    assert (order["status"], order["awb_number"]) == ("OUT_FOR_DELIVERY", "DTDC12345")
    assert order["timeline"][-1]["reason"] == "Courier: Out For Delivery"
    assert n1 == order["order_number"]


def test_every_suggested_status_word_is_understood():
    for word in CANONICAL_STATUS_WORDS:
        assert parser_norm(word) in STATUS_WORDS, word

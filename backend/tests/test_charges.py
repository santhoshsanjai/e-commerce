import pytest

from app.modules.pricing.schemas import Charges
from app.modules.pricing.service import Line, line_gst, quote
from tests.helpers import admin_id, auth, place_order, published_product

CHARGES = "/api/v1/admin/charges"


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def charges(**kw):
    base = {
        "shipping_fee_minor": 4000,
        "free_shipping_over_minor": None,
        "prices_include_gst": True,
        "default_gst_rate_bp": 1800,
    }
    return {**base, **kw}


def test_gst_is_worked_out_per_line_and_rounded_half_up():
    # ₹118 including 18% GST holds ₹18 of GST.
    assert line_gst(11800, 1800, prices_include_gst=True) == 1800
    # ₹100 + 18% adds ₹18.
    assert line_gst(10000, 1800, prices_include_gst=False) == 1800
    # ₹0.05 at 5%: 0.25 paise rounds down; ₹0.10: 0.5 paise rounds up.
    assert line_gst(5, 500, prices_include_gst=False) == 0
    assert line_gst(10, 500, prices_include_gst=False) == 1
    assert line_gst(10000, 0, prices_include_gst=True) == 0


def test_quote_applies_product_rates_free_delivery_and_tax_mode():
    lines = [Line(11800, None), Line(10500, 500)]
    inc = quote(Charges(**charges()), lines)
    assert (inc.subtotal_minor, inc.shipping_minor, inc.tax_minor) == (22300, 4000, 0)
    assert inc.line_rates_bp == (1800, 500)
    assert inc.gst_minor == 1800 + 500
    assert inc.total_minor == 26300

    exc = quote(Charges(**charges(prices_include_gst=False, free_shipping_over_minor=20000)), lines)
    assert exc.shipping_minor == 0  # 22300 >= 20000
    assert exc.tax_minor == exc.gst_minor == 2124 + 525
    assert exc.total_minor == 22300 + 2649

    assert quote(Charges(**charges()), []).shipping_minor == 0


def test_only_settings_managers_can_change_charges(client, staff_token, admin):
    manager = auth(staff_token("Manager"))
    assert client.get(CHARGES, headers=manager).status_code == 403
    assert client.put(CHARGES, json=charges(), headers=manager).status_code == 403

    assert client.get(CHARGES, headers=admin).json()["default_gst_rate_bp"] == 1800
    saved = client.put(CHARGES, json=charges(free_shipping_over_minor=99900), headers=admin)
    assert saved.status_code == 200, saved.text
    assert client.get(CHARGES, headers=admin).json() == charges(free_shipping_over_minor=99900)

    bad = client.put(CHARGES, json=charges(default_gst_rate_bp=5000), headers=admin)
    assert bad.status_code == 422
    waive_nothing = client.put(
        CHARGES, json=charges(shipping_fee_minor=0, free_shipping_over_minor=50000), headers=admin
    )
    assert waive_nothing.status_code == 422

    log = client.get(
        "/api/v1/admin/audit-logs", params={"action": "charges.updated"}, headers=admin
    )
    assert log.json()["total"] == 1


def test_cart_and_order_use_the_rules_and_the_order_keeps_them(client, buyer_token, admin):
    client.put(
        CHARGES,
        json=charges(prices_include_gst=False, free_shipping_over_minor=200000),
        headers=admin,
    )
    order, _ = place_order(client, buyer_token, admin, price=10000)
    assert order["subtotal_minor"] == 10000
    assert order["shipping_minor"] == 4000
    assert order["tax_minor"] == order["gst_minor"] == 1800
    assert order["prices_include_gst"] is False
    assert order["total_minor"] == 15800
    assert order["items"][0]["gst_rate_bp"] == 1800

    # Changing the rules later doesn't touch the placed order.
    client.put(CHARGES, json=charges(shipping_fee_minor=0), headers=admin)
    oid = admin_id(client, admin, order["order_number"])
    again = client.get(f"/api/v1/admin/orders/{oid}", headers=admin).json()
    assert again["total_minor"] == 15800


def test_a_products_own_rate_beats_the_default_and_shows_in_the_cart(client, buyer_token, admin):
    product = published_product(client, admin, price=10500)
    resp = client.patch(
        f"/api/v1/admin/products/{product['id']}", json={"gst_rate_bp": 500}, headers=admin
    )
    assert resp.status_code == 200 and resp.json()["gst_rate_bp"] == 500
    buyer = auth(buyer_token())
    client.post(
        "/api/v1/cart/items", json={"sku_id": product["sku"]["id"], "qty": 1}, headers=buyer
    )
    cart = client.get("/api/v1/cart", headers=buyer).json()
    assert cart["gst_minor"] == 500  # ₹105 including 5%
    assert cart["prices_include_gst"] is True
    assert cart["tax_minor"] == 0
    assert cart["total_minor"] == 10500 + cart["shipping_minor"]

    # Back to the shop default.
    resp = client.patch(
        f"/api/v1/admin/products/{product['id']}", json={"gst_rate_bp": None}, headers=admin
    )
    assert resp.json()["gst_rate_bp"] is None

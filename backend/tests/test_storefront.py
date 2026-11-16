import pytest

from tests.helpers import auth

PUBLIC = "/api/v1/storefront"
ADMIN = "/api/v1/admin/storefront"


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def test_defaults_before_anything_is_saved(client):
    resp = client.get(PUBLIC)
    assert resp.status_code == 200
    assert resp.json() == {"store_name": "Shop", "announcement": "", "colors": {}}
    assert "max-age" in resp.headers["cache-control"]


def test_admin_saves_name_announcement_and_colours(client, admin):
    body = {
        "store_name": "  Maison Atelier ",
        "announcement": "Free UK delivery over £50",
        "colors": {"primary": "#1C2B39", "accent": "#b08d57"},
    }
    resp = client.put(ADMIN, json=body, headers=admin)
    assert resp.status_code == 200, resp.text
    saved = {
        "store_name": "Maison Atelier",
        "announcement": "Free UK delivery over £50",
        "colors": {"primary": "#1c2b39", "accent": "#b08d57"},
    }
    assert resp.json() == saved
    assert client.get(PUBLIC).json() == saved
    assert client.get(ADMIN, headers=admin).json() == saved

    # Saving again replaces the overrides: an empty map resets every colour to its default.
    resp = client.put(ADMIN, json={"store_name": "Maison", "colors": {}}, headers=admin)
    assert resp.json()["colors"] == {}

    actions = client.get("/api/v1/admin/audit-logs/actions", headers=admin).json()
    assert "storefront.updated" in actions


@pytest.mark.parametrize(
    "colors",
    [
        {"primary": "red"},
        {"primary": "#12345"},
        {"primary": "#1234567"},
        {"Primary": "#123456"},
        {"primary;}body{": "#123456"},
        {f"c{i}": "#123456" for i in range(41)},
    ],
)
def test_rejects_bad_colours(client, admin, colors):
    resp = client.put(ADMIN, json={"store_name": "Shop", "colors": colors}, headers=admin)
    assert resp.status_code == 422


def test_rejects_blank_name(client, admin):
    resp = client.put(ADMIN, json={"store_name": "   "}, headers=admin)
    assert resp.status_code == 422


def test_manager_cannot_change_the_look(client, staff_token):
    manager = auth(staff_token("Manager"))
    resp = client.put(ADMIN, json={"store_name": "Mine"}, headers=manager)
    assert resp.status_code == 403

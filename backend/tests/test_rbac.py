import re
import uuid

import pytest

from app.modules.access_control.permissions import DEFAULT_ROLE_GRANTS, PERMISSIONS

# Every admin endpoint and the permission it needs. New admin routes must be added here;
# test_every_admin_route_is_in_the_matrix fails otherwise.
ADMIN_ENDPOINTS = [
    ("GET", "/api/v1/admin/staff", "users.view"),
    ("POST", "/api/v1/admin/staff", "users.manage"),
    ("GET", "/api/v1/admin/roles", "roles.view"),
    ("GET", "/api/v1/admin/permissions", "roles.view"),
    ("GET", "/api/v1/admin/categories", "categories.view"),
    ("POST", "/api/v1/admin/categories", "categories.manage"),
    ("PATCH", "/api/v1/admin/categories/{category_id}", "categories.manage"),
    ("GET", "/api/v1/admin/products", "products.view"),
    ("POST", "/api/v1/admin/products", "products.create"),
    ("GET", "/api/v1/admin/products/{product_id}", "products.view"),
    ("PATCH", "/api/v1/admin/products/{product_id}", "products.update"),
    ("POST", "/api/v1/admin/products/{product_id}/publish", "products.publish"),
    ("POST", "/api/v1/admin/products/{product_id}/unpublish", "products.publish"),
    ("POST", "/api/v1/admin/products/{product_id}/archive", "products.archive"),
    ("POST", "/api/v1/admin/products/{product_id}/media", "products.update"),
    ("DELETE", "/api/v1/admin/products/{product_id}/media/{media_id}", "products.update"),
    ("GET", "/api/v1/admin/orders", "orders.view"),
    ("GET", "/api/v1/admin/orders/{order_id}", "orders.view"),
    ("GET", "/api/v1/admin/dispatch-batches", "orders.export"),
    ("POST", "/api/v1/admin/dispatch-batches", "orders.export"),
    ("GET", "/api/v1/admin/dispatch-batches/eligible-orders", "orders.export"),
    ("GET", "/api/v1/admin/dispatch-batches/{batch_id}", "orders.export"),
    ("GET", "/api/v1/admin/dispatch-batches/{batch_id}/file", "orders.export"),
]


def concrete(path: str) -> str:
    """Fill path parameters with random IDs; authorization runs before any lookup."""
    return re.sub(r"\{[^}]+\}", lambda _: str(uuid.uuid4()), path)


def test_every_admin_route_is_in_the_matrix():
    from app.main import app

    routes = {
        (method.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        if path.startswith("/api/v1/admin")
        for method in ops
    }
    assert routes == {(m, p) for m, p, _ in ADMIN_ENDPOINTS}


def test_seeded_roles_match_defaults(client, staff_token):
    token = staff_token("Super Admin")
    roles = client.get("/api/v1/admin/roles", headers={"Authorization": f"Bearer {token}"}).json()
    assert {r["name"]: sorted(r["permissions"]) for r in roles} == {
        name: sorted(keys) for name, keys in DEFAULT_ROLE_GRANTS.items()
    }
    assert sorted(DEFAULT_ROLE_GRANTS["Super Admin"]) == sorted(PERMISSIONS)


@pytest.mark.parametrize("role", ["Super Admin", "Admin", "Manager"])
@pytest.mark.parametrize(("method", "path", "permission"), ADMIN_ENDPOINTS)
def test_permission_matrix(client, staff_token, role, method, path, permission):
    token = staff_token(role)
    body = {} if method in ("POST", "PATCH") else None
    resp = client.request(
        method, concrete(path), json=body, headers={"Authorization": f"Bearer {token}"}
    )
    if permission in DEFAULT_ROLE_GRANTS[role]:
        # Past authorization: then success, validation failure or not-found for the random ID.
        assert resp.status_code in (200, 404, 422), resp.text
    else:
        assert resp.status_code == 403, resp.text


@pytest.mark.parametrize(("method", "path", "permission"), ADMIN_ENDPOINTS)
def test_admin_routes_require_authentication(client, method, path, permission):
    assert client.request(method, concrete(path)).status_code == 401


def test_buyer_token_cannot_reach_admin_routes(client):
    buyer = {"email": "b@example.com", "password": "buyer-password-1", "full_name": "B"}
    client.post("/api/v1/auth/register", json=buyer)
    token = client.post("/api/v1/auth/login", json=buyer).json()["access_token"]
    for method, path, _ in ADMIN_ENDPOINTS:
        resp = client.request(method, concrete(path), headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


def test_staff_without_roles_has_no_access(client, staff_token):
    token = staff_token()
    resp = client.get("/api/v1/admin/roles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

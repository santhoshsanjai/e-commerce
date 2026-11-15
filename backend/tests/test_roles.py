def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _roles(client, token):
    return {r["name"]: r for r in client.get("/api/v1/admin/roles", headers=_auth(token)).json()}


def test_create_edit_and_delete_custom_role(client, staff_token):
    token = staff_token("Super Admin")
    resp = client.post(
        "/api/v1/admin/roles",
        json={
            "name": "Warehouse",
            "description": "Packs orders",
            "permissions": ["orders.view", "orders.export"],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    role = resp.json()
    assert role["permissions"] == ["orders.export", "orders.view"]
    assert (role["is_system"], role["user_count"]) == (False, 0)

    resp = client.patch(
        f"/api/v1/admin/roles/{role['id']}",
        json={"name": "Warehouse team", "permissions": ["orders.view"]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert (resp.json()["name"], resp.json()["permissions"]) == ("Warehouse team", ["orders.view"])

    assert (
        client.delete(f"/api/v1/admin/roles/{role['id']}", headers=_auth(token)).status_code == 204
    )
    assert "Warehouse team" not in _roles(client, token)

    from sqlalchemy import select

    from app.infrastructure.database import SessionLocal
    from app.modules.audit.models import AuditLog

    with SessionLocal() as db:
        actions = set(db.scalars(select(AuditLog.action)).all())
    assert {"roles.created", "roles.updated", "roles.deleted"} <= actions


def test_editing_admin_role_permissions_takes_effect(client, staff_token):
    token = staff_token("Super Admin")
    admin_token = staff_token("Admin")
    admin = _roles(client, token)["Admin"]
    perms = sorted(set(admin["permissions"]) - {"reports.view"})
    resp = client.patch(
        f"/api/v1/admin/roles/{admin['id']}", json={"permissions": perms}, headers=_auth(token)
    )
    assert resp.status_code == 200
    me = client.get("/api/v1/auth/me", headers=_auth(admin_token)).json()
    assert "reports.view" not in me["permissions"]


def test_super_admin_role_is_locked(client, staff_token):
    token = staff_token("Super Admin")
    sa = _roles(client, token)["Super Admin"]
    resp = client.patch(
        f"/api/v1/admin/roles/{sa['id']}", json={"permissions": []}, headers=_auth(token)
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "super_admin_locked"


def test_system_roles_cannot_be_renamed_or_deleted(client, staff_token):
    token = staff_token("Super Admin")
    manager = _roles(client, token)["Manager"]
    rename = client.patch(
        f"/api/v1/admin/roles/{manager['id']}", json={"name": "Boss"}, headers=_auth(token)
    )
    assert rename.status_code == 409
    delete = client.delete(f"/api/v1/admin/roles/{manager['id']}", headers=_auth(token))
    assert delete.status_code == 409
    assert delete.json()["error"]["code"] == "system_role"


def test_role_in_use_cannot_be_deleted(client, staff_token, make_staff):
    token = staff_token("Super Admin")
    role = client.post(
        "/api/v1/admin/roles", json={"name": "Packers", "permissions": []}, headers=_auth(token)
    ).json()
    creds = make_staff("Packers")
    assert creds
    assert _roles(client, token)["Packers"]["user_count"] == 1
    resp = client.delete(f"/api/v1/admin/roles/{role['id']}", headers=_auth(token))
    assert resp.status_code == 409
    assert resp.json()["error"]["details"] == {"user_count": 1}


def test_duplicate_name_and_unknown_permission(client, staff_token):
    token = staff_token("Super Admin")
    dup = client.post("/api/v1/admin/roles", json={"name": "Admin"}, headers=_auth(token))
    assert dup.status_code == 409
    bad = client.post(
        "/api/v1/admin/roles",
        json={"name": "X", "permissions": ["nope.nothing"]},
        headers=_auth(token),
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["details"] == {"unknown": ["nope.nothing"]}


def test_cannot_grant_permissions_you_do_not_hold(client, staff_token, make_staff):
    """Give a custom role roles.manage only; it still can't hand out users.manage."""
    token = staff_token("Super Admin")
    client.post(
        "/api/v1/admin/roles",
        json={"name": "Role editor", "permissions": ["roles.view", "roles.manage"]},
        headers=_auth(token),
    )
    creds = make_staff("Role editor")
    editor = client.post("/api/v1/auth/staff/login", json=creds).json()["access_token"]
    resp = client.post(
        "/api/v1/admin/roles",
        json={"name": "Sneaky", "permissions": ["users.manage"]},
        headers=_auth(editor),
    )
    assert resp.status_code == 403
    ok = client.post(
        "/api/v1/admin/roles",
        json={"name": "Viewer", "permissions": ["roles.view"]},
        headers=_auth(editor),
    )
    assert ok.status_code == 201

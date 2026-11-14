def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _role_id(client, token, name):
    roles = client.get("/api/v1/admin/roles", headers=_auth(token)).json()
    return next(r["id"] for r in roles if r["name"] == name)


def test_super_admin_creates_manager_and_it_is_audited(client, staff_token):
    token = staff_token("Super Admin")
    payload = {
        "email": "New.Manager@Example.com",
        "full_name": "New Manager",
        "password": "manager-password-1",
        "role_ids": [_role_id(client, token, "Manager")],
    }
    resp = client.post("/api/v1/admin/staff", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    assert resp.json()["roles"] == ["Manager"]
    assert resp.json()["email"] == "new.manager@example.com"

    login = client.post(
        "/api/v1/auth/staff/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    me = client.get("/api/v1/auth/me", headers=_auth(login.json()["access_token"])).json()
    assert "orders.export" in me["permissions"]
    assert "users.manage" not in me["permissions"]

    from sqlalchemy import select

    from app.infrastructure.database import SessionLocal
    from app.modules.audit.models import AuditLog

    with SessionLocal() as db:
        actions = set(db.scalars(select(AuditLog.action)).all())
    assert {"users.staff_created", "auth.staff_login"} <= actions


def test_only_super_admin_can_grant_super_admin(client, staff_token):
    # No seeded non-Super-Admin role holds users.manage yet, so exercise the service rule
    # directly with an Admin actor.
    from fastapi import Request

    from app.core.exceptions import PermissionDenied
    from app.infrastructure.database import SessionLocal
    from app.modules.access_control.models import Role
    from app.modules.users import service
    from app.modules.users.models import User
    from app.modules.users.schemas import StaffCreate

    staff_token("Admin")
    with SessionLocal() as db:
        actor = db.query(User).one()
        super_role = db.query(Role).filter_by(name="Super Admin").one()
        data = StaffCreate(
            email="x@example.com",
            full_name="X",
            password="x-password-12345",
            role_ids=[super_role.id],
        )
        request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})
        try:
            service.create_staff(db, data, actor, request)
            raise AssertionError("expected PermissionDenied")
        except PermissionDenied:
            pass


def test_staff_list_is_paginated(client, staff_token):
    token = staff_token("Super Admin")
    resp = client.get("/api/v1/admin/staff?page=1&page_size=1", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["page_size"] == 1
    assert len(body["items"]) == 1

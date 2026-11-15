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


# --- Phase 2b: editing staff -------------------------------------------------


def _staff_id(client, token, email):
    items = client.get(f"/api/v1/admin/staff?q={email}", headers=_auth(token)).json()["items"]
    return next(i["id"] for i in items if i["email"] == email)


def _login(client, creds):
    return client.post("/api/v1/auth/staff/login", json=creds)


def _audit_actions():
    from sqlalchemy import select

    from app.infrastructure.database import SessionLocal
    from app.modules.audit.models import AuditLog

    with SessionLocal() as db:
        return list(db.scalars(select(AuditLog.action)).all())


def test_edit_staff_name_phone_and_roles(client, staff_token, make_staff):
    token = staff_token("Super Admin")
    target = make_staff("Manager")
    sid = _staff_id(client, token, target["email"])
    admin_role = _role_id(client, token, "Admin")

    resp = client.patch(
        f"/api/v1/admin/staff/{sid}",
        json={"full_name": " Priya S ", "phone": "+91 98765 43210", "role_ids": [admin_role]},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["full_name"], body["phone"], body["roles"]) == (
        "Priya S",
        "+91 98765 43210",
        ["Admin"],
    )
    assert body["role_ids"] == [admin_role]

    me = client.get(
        "/api/v1/auth/me", headers=_auth(_login(client, target).json()["access_token"])
    ).json()
    assert "reports.view" in me["permissions"]
    assert "users.staff_updated" in _audit_actions()


def test_deactivating_staff_blocks_login_and_ends_sessions(client, staff_token, make_staff):
    token = staff_token("Super Admin")
    target = make_staff("Manager")
    session = _login(client, target)
    target_token = session.json()["access_token"]
    refresh_cookie = dict(session.cookies)
    sid = _staff_id(client, token, target["email"])

    resp = client.patch(
        f"/api/v1/admin/staff/{sid}", json={"is_active": False}, headers=_auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Existing access token stops working at once; refresh and login are refused.
    assert client.get("/api/v1/auth/me", headers=_auth(target_token)).status_code == 401
    client.cookies.clear()
    client.cookies.update(refresh_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.clear()
    assert _login(client, target).status_code == 401
    assert "users.staff_deactivated" in _audit_actions()

    from sqlalchemy import select

    from app.infrastructure.database import SessionLocal
    from app.modules.auth.models import RefreshToken

    with SessionLocal() as db:
        live = db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == sid, RefreshToken.revoked_at.is_(None)
            )
        ).all()
    assert live == []

    # Reactivating lets them log in again.
    client.patch(f"/api/v1/admin/staff/{sid}", json={"is_active": True}, headers=_auth(token))
    assert _login(client, target).status_code == 200


def test_cannot_change_own_roles_or_deactivate_self(client, make_staff):
    me = make_staff("Super Admin")
    token = _login(client, me).json()["access_token"]
    sid = _staff_id(client, token, me["email"])
    for change in ({"is_active": False}, {"role_ids": [_role_id(client, token, "Manager")]}):
        resp = client.patch(f"/api/v1/admin/staff/{sid}", json=change, headers=_auth(token))
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "cannot_change_own_access"
    # Own name is fine.
    resp = client.patch(
        f"/api/v1/admin/staff/{sid}", json={"full_name": "Me"}, headers=_auth(token)
    )
    assert resp.status_code == 200


def test_last_super_admin_cannot_be_removed(client, make_staff):
    """Exercise the guard directly: the HTTP route already refuses self-changes."""
    from fastapi import Request

    from app.core.exceptions import AppError
    from app.infrastructure.database import SessionLocal
    from app.modules.users import service
    from app.modules.users.models import User
    from app.modules.users.schemas import StaffUpdate

    a = make_staff("Super Admin")
    b = make_staff("Super Admin")
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})
    with SessionLocal() as db:
        actor = db.query(User).filter_by(email=a["email"]).one()
        target = db.query(User).filter_by(email=b["email"]).one()
        actor_id, target_id = actor.id, target.id
        # Deactivate A behind the API's back, so B is the only active Super Admin left.
        actor.is_active = False
        db.commit()
        try:
            service.update_staff(db, target_id, StaffUpdate(is_active=False), actor, request)
            raise AssertionError("expected last_super_admin")
        except AppError as exc:
            assert exc.code == "last_super_admin"
        db.rollback()
        assert db.get(User, actor_id) is not None


def test_only_super_admin_can_edit_a_super_admin(client, staff_token, make_staff):
    from fastapi import Request

    from app.core.exceptions import PermissionDenied
    from app.infrastructure.database import SessionLocal
    from app.modules.users import service
    from app.modules.users.models import User
    from app.modules.users.schemas import StaffUpdate

    admin = make_staff("Admin")
    boss = make_staff("Super Admin")
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})
    with SessionLocal() as db:
        actor = db.query(User).filter_by(email=admin["email"]).one()
        target = db.query(User).filter_by(email=boss["email"]).one()
        for call in (
            lambda: service.update_staff(db, target.id, StaffUpdate(full_name="X"), actor, request),
            lambda: service.reset_password(db, target.id, "new-password-123", actor, request),
        ):
            try:
                call()
                raise AssertionError("expected PermissionDenied")
            except PermissionDenied:
                db.rollback()


def test_reset_password(client, staff_token, make_staff):
    token = staff_token("Super Admin")
    target = make_staff("Manager")
    sid = _staff_id(client, token, target["email"])
    resp = client.post(
        f"/api/v1/admin/staff/{sid}/password",
        json={"password": "brand-new-pass-1"},
        headers=_auth(token),
    )
    assert resp.status_code == 204
    assert _login(client, target).status_code == 401
    assert _login(client, {**target, "password": "brand-new-pass-1"}).status_code == 200
    assert "users.password_reset" in _audit_actions()

    short = client.post(
        f"/api/v1/admin/staff/{sid}/password", json={"password": "short"}, headers=_auth(token)
    )
    assert short.status_code == 422


def test_staff_list_filters(client, staff_token, make_staff):
    token = staff_token("Super Admin")
    m = make_staff("Manager")
    make_staff("Admin")
    sid = _staff_id(client, token, m["email"])
    client.patch(f"/api/v1/admin/staff/{sid}", json={"is_active": False}, headers=_auth(token))

    def emails(query):
        resp = client.get(f"/api/v1/admin/staff?{query}", headers=_auth(token))
        return {i["email"] for i in resp.json()["items"]}

    assert emails(f"role_id={_role_id(client, token, 'Manager')}") == {m["email"]}
    assert emails("status=inactive") == {m["email"]}
    assert m["email"] not in emails("status=active")
    assert emails("q=STAFF2") == {m["email"]}


def test_unknown_staff_is_404(client, staff_token):
    import uuid

    token = staff_token("Super Admin")
    resp = client.get(f"/api/v1/admin/staff/{uuid.uuid4()}", headers=_auth(token))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "staff_not_found"

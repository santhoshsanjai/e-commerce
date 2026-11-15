from tests.helpers import auth

BUYER = {"email": "neha@example.com", "password": "buyer-password-1", "full_name": "Neha"}


def _register_and_login(client):
    client.post("/api/v1/auth/register", json=BUYER)
    resp = client.post(
        "/api/v1/auth/login", json={"email": BUYER["email"], "password": BUYER["password"]}
    )
    assert resp.status_code == 200
    return resp


def test_update_profile(client):
    h = auth(_register_and_login(client).json()["access_token"])
    resp = client.patch(
        "/api/v1/auth/me",
        json={"full_name": "  Neha Sharma ", "phone": "+91 98765 43210"},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    assert (resp.json()["full_name"], resp.json()["phone"]) == ("Neha Sharma", "+91 98765 43210")
    assert resp.json()["email"] == BUYER["email"]

    # Empty phone clears it; name left alone.
    resp = client.patch("/api/v1/auth/me", json={"phone": ""}, headers=h)
    assert (resp.json()["full_name"], resp.json()["phone"]) == ("Neha Sharma", None)


def test_profile_validation(client):
    h = auth(_register_and_login(client).json()["access_token"])
    assert client.patch("/api/v1/auth/me", json={"full_name": "   "}, headers=h).status_code == 422
    assert client.patch("/api/v1/auth/me", json={"phone": "call me"}, headers=h).status_code == 422
    # Email is not editable here: unknown fields are ignored.
    resp = client.patch("/api/v1/auth/me", json={"email": "x@example.com"}, headers=h)
    assert resp.json()["email"] == BUYER["email"]


def test_change_password_signs_out_other_devices(client):
    other_device = _register_and_login(client)
    other_cookie = dict(other_device.cookies)
    this_device = client.post(
        "/api/v1/auth/login", json={"email": BUYER["email"], "password": BUYER["password"]}
    )
    h = auth(this_device.json()["access_token"])

    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": BUYER["password"], "new_password": "fresh-password-9"},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]
    new_cookie = resp.cookies.get("refresh_token")
    assert new_cookie

    # The other device's refresh token no longer works; this device's new one does.
    client.cookies.clear()
    client.cookies.update(other_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.clear()
    client.cookies.set("refresh_token", new_cookie, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 200
    client.cookies.clear()

    old = client.post(
        "/api/v1/auth/login", json={"email": BUYER["email"], "password": BUYER["password"]}
    )
    assert old.status_code == 401
    new = client.post(
        "/api/v1/auth/login", json={"email": BUYER["email"], "password": "fresh-password-9"}
    )
    assert new.status_code == 200


def test_change_password_rules(client, staff_token):
    h = auth(_register_and_login(client).json()["access_token"])

    def change(current, new, headers=h):
        return client.post(
            "/api/v1/auth/change-password",
            json={"current_password": current, "new_password": new},
            headers=headers,
        )

    wrong = change("not-my-password", "fresh-password-9")
    assert (wrong.status_code, wrong.json()["error"]["code"]) == (400, "wrong_password")
    same = change(BUYER["password"], BUYER["password"])
    assert same.json()["error"]["code"] == "password_unchanged"
    assert change(BUYER["password"], "short").status_code == 422

    staff = auth(staff_token("Manager"))
    too_short = change("staff-password-123", "elevenchars", headers=staff)
    assert too_short.json()["error"]["code"] == "password_too_short"
    assert change("staff-password-123", "a-long-staff-pass", headers=staff).status_code == 200


def test_change_password_is_rate_limited(client):
    h = auth(_register_and_login(client).json()["access_token"])
    codes = [
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": f"guess-{i}", "new_password": "fresh-password-9"},
            headers=h,
        ).status_code
        for i in range(12)
    ]
    assert 429 in codes


def test_password_change_is_audited(client, staff_token):
    from sqlalchemy import select

    from app.infrastructure.database import SessionLocal
    from app.modules.audit.models import AuditLog

    h = auth(_register_and_login(client).json()["access_token"])
    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": BUYER["password"], "new_password": "fresh-password-9"},
        headers=h,
    )
    with SessionLocal() as db:
        assert "auth.password_changed" in set(db.scalars(select(AuditLog.action)).all())

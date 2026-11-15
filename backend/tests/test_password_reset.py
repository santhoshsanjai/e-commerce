import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

BUYER = {"email": "reset@example.com", "password": "buyer-password-1", "full_name": "Ravi Buyer"}
NEW_PASSWORD = "brand-new-password-2"


def _link_token(email) -> str:
    match = re.search(r"/reset-password\?token=([\w-]+)", email.text)
    assert match, email.text
    return match.group(1)


def _request(client, email=BUYER["email"]):
    return client.post("/api/v1/auth/password-reset", json={"email": email})


def test_reset_link_sets_new_password_and_signs_out_everywhere(client, outbox):
    client.post("/api/v1/auth/register", json=BUYER)
    assert client.post("/api/v1/auth/login", json=BUYER).status_code == 200
    old_cookie = client.cookies.get("refresh_token")

    resp = _request(client, "Reset@Example.com")
    assert resp.status_code == 202
    [email] = outbox.sent
    assert email.to == "reset@example.com"
    assert email.text.count("http://localhost:4200/reset-password?token=") == 1

    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": _link_token(email), "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 204
    assert outbox.sent[-1].subject == "Your password was changed"

    creds = {"email": BUYER["email"], "password": BUYER["password"]}
    assert client.post("/api/v1/auth/login", json=creds).status_code == 401
    assert (
        client.post("/api/v1/auth/login", json={**creds, "password": NEW_PASSWORD}).status_code
        == 200
    )
    client.cookies.clear()
    client.cookies.set("refresh_token", old_cookie, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_unknown_email_gets_the_same_answer_and_no_email(client, outbox):
    client.post("/api/v1/auth/register", json=BUYER)
    known = _request(client)
    unknown = _request(client, "nobody@example.com")
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert len(outbox.sent) == 1


def test_link_works_once(client, outbox):
    client.post("/api/v1/auth/register", json=BUYER)
    _request(client)
    token = _link_token(outbox.sent[0])
    body = {"token": token, "new_password": NEW_PASSWORD}
    assert client.post("/api/v1/auth/password-reset/confirm", json=body).status_code == 204
    again = client.post(
        "/api/v1/auth/password-reset/confirm", json={**body, "new_password": "another-pass-33"}
    )
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "reset_link_invalid"


def test_new_link_cancels_the_old_one(client, outbox):
    client.post("/api/v1/auth/register", json=BUYER)
    _request(client)
    _request(client)
    first, second = (_link_token(e) for e in outbox.sent)
    body = {"new_password": NEW_PASSWORD}
    resp = client.post("/api/v1/auth/password-reset/confirm", json={**body, "token": first})
    assert resp.status_code == 400
    resp = client.post("/api/v1/auth/password-reset/confirm", json={**body, "token": second})
    assert resp.status_code == 204


def test_expired_link_is_refused(client, outbox):
    from app.infrastructure.database import engine
    from app.modules.auth.models import PasswordResetToken

    client.post("/api/v1/auth/register", json=BUYER)
    _request(client)
    with engine.begin() as conn:
        conn.execute(
            update(PasswordResetToken).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": _link_token(outbox.sent[0]), "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 400


def test_made_up_token_is_refused(client):
    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "x" * 43, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "reset_link_invalid"


def test_deactivated_account_gets_no_email(client, outbox, make_staff):
    from app.infrastructure.database import SessionLocal
    from app.modules.users.models import User

    staff = make_staff("Manager")
    with SessionLocal() as db:
        db.execute(update(User).where(User.email == staff["email"]).values(is_active=False))
        db.commit()
    assert _request(client, staff["email"]).status_code == 202
    assert outbox.sent == []


def test_staff_link_points_to_admin_site_and_needs_a_long_password(client, outbox, make_staff):
    staff = make_staff("Manager")
    _request(client, staff["email"])
    [email] = outbox.sent
    assert "http://localhost:4300/reset-password?token=" in email.text
    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": _link_token(email), "new_password": "eleven-char"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "password_too_short"


def test_reset_emails_are_rate_limited(client, outbox):
    client.post("/api/v1/auth/register", json=BUYER)
    codes = [_request(client).status_code for _ in range(5)]
    assert codes == [202] * 5
    assert len(outbox.sent) == 3


def test_password_reset_is_audited(client, outbox, staff_token):
    client.post("/api/v1/auth/register", json=BUYER)
    _request(client)
    client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": _link_token(outbox.sent[0]), "new_password": NEW_PASSWORD},
    )
    token = staff_token("Super Admin")
    resp = client.get(
        "/api/v1/admin/audit-logs",
        params={"action": "auth.password_reset"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["total"] == 1


def test_change_password_sends_a_notice(client, outbox):
    client.post("/api/v1/auth/register", json=BUYER)
    token = client.post("/api/v1/auth/login", json=BUYER).json()["access_token"]
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": BUYER["password"], "new_password": NEW_PASSWORD},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert [e.subject for e in outbox.sent] == ["Your password was changed"]

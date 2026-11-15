BUYER = {
    "email": "Buyer@Example.com",
    "password": "buyer-password-1",
    "full_name": "Asha Buyer",
}


def register_and_login(client):
    assert client.post("/api/v1/auth/register", json=BUYER).status_code == 201
    resp = client.post(
        "/api/v1/auth/login", json={"email": BUYER["email"], "password": BUYER["password"]}
    )
    assert resp.status_code == 200, resp.text
    return resp


def test_register_normalises_email_and_hides_password(client):
    resp = client.post("/api/v1/auth/register", json=BUYER)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "buyer@example.com"
    assert body["user_type"] == "BUYER"
    assert body["permissions"] == []
    assert "password" not in str(body)


def test_register_duplicate_email_is_conflict(client):
    client.post("/api/v1/auth/register", json=BUYER)
    resp = client.post("/api/v1/auth/register", json={**BUYER, "email": "buyer@example.com"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


def test_register_rejects_short_password(client):
    resp = client.post("/api/v1/auth/register", json={**BUYER, "password": "short"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_login_sets_httponly_refresh_cookie_and_me_works(client):
    resp = register_and_login(client)
    cookie = resp.headers["set-cookie"]
    assert "refresh_token=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert "SameSite=strict" in cookie
    token = resp.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "buyer@example.com"


def test_wrong_password_is_generic_401(client):
    client.post("/api/v1/auth/register", json=BUYER)
    resp = client.post(
        "/api/v1/auth/login", json={"email": BUYER["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-1"}
    )
    assert unknown.json()["error"] == {
        **resp.json()["error"],
        "request_id": unknown.json()["error"]["request_id"],
    }


def test_buyer_cannot_use_staff_login_and_staff_cannot_use_buyer_login(client, make_staff):
    client.post("/api/v1/auth/register", json=BUYER)
    resp = client.post(
        "/api/v1/auth/staff/login", json={"email": BUYER["email"], "password": BUYER["password"]}
    )
    assert resp.status_code == 401
    staff = make_staff("Admin")
    assert client.post("/api/v1/auth/login", json=staff).status_code == 401


def test_refresh_rotates_token(client):
    first = register_and_login(client).cookies["refresh_token"]
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    second = resp.cookies["refresh_token"]
    assert second != first
    assert resp.json()["access_token"]


def test_reusing_rotated_refresh_token_revokes_family(client):
    old = register_and_login(client).cookies["refresh_token"]
    new = client.post("/api/v1/auth/refresh").cookies["refresh_token"]
    client.cookies.clear()
    # Attacker replays the old token: rejected, and the legitimate new token dies too.
    client.cookies.set("refresh_token", old, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.clear()
    client.cookies.set("refresh_token", new, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_session(client):
    register_and_login(client)
    token = client.cookies.get("refresh_token")
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set("refresh_token", token, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_login_is_rate_limited(client):
    client.post("/api/v1/auth/register", json=BUYER)
    bad = {"email": BUYER["email"], "password": "wrong-password"}
    codes = [client.post("/api/v1/auth/login", json=bad).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429


def test_successful_logins_do_not_lock_the_account(client):
    """Only failures count: someone who signs in often (or after a typo) is never locked out."""
    client.post("/api/v1/auth/register", json=BUYER)
    good = {"email": BUYER["email"], "password": BUYER["password"]}
    bad = {"email": BUYER["email"], "password": "wrong-password"}
    for _ in range(8):
        assert client.post("/api/v1/auth/login", json=good).status_code == 200
    # Four typos, then the right password, then four more typos: still not locked.
    for _ in range(2):
        for _ in range(4):
            assert client.post("/api/v1/auth/login", json=bad).status_code == 401
        assert client.post("/api/v1/auth/login", json=good).status_code == 200


def test_tampered_token_rejected(client):
    token = register_and_login(client).json()["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}x"})
    assert resp.status_code == 401


def test_one_address_trying_many_accounts_is_rate_limited(client):
    """Spreading guesses over many accounts doesn't get round the limit."""
    codes = [
        client.post(
            "/api/v1/auth/login", json={"email": f"user{i}@example.com", "password": "guess-123"}
        ).status_code
        for i in range(31)
    ]
    assert codes[:30] == [401] * 30
    assert codes[30] == 429


def test_rate_limit_is_shared_between_api_instances(client):
    """Counts live in the database, so a second API instance sees the same failures."""
    from sqlalchemy import text

    from app.infrastructure.database import engine

    client.post("/api/v1/auth/register", json=BUYER)
    bad = {"email": BUYER["email"], "password": "wrong-password"}
    for _ in range(5):
        client.post("/api/v1/auth/login", json=bad)
    with engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM rate_limit_hits WHERE key = 'account:buyer@example.com'")
            )
            == 5
        )


def test_api_responses_are_not_cached_or_framed(client):
    resp = client.post("/api/v1/auth/register", json=BUYER)
    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-content-type-options"] == "nosniff"

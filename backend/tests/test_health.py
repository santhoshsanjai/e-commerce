def test_live(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_checks_database(client):
    assert client.get("/health/ready").json() == {"status": "ok"}


def test_request_id_is_echoed_or_generated(client):
    assert (
        client.get("/health/live", headers={"X-Request-ID": "abc123"}).headers["X-Request-ID"]
        == "abc123"
    )
    assert len(client.get("/health/live").headers["X-Request-ID"]) == 32


def test_error_format_includes_request_id(client):
    resp = client.get("/api/v1/auth/me", headers={"X-Request-ID": "req-1"})
    assert resp.status_code == 401
    body = resp.json()["error"]
    assert body["code"] == "not_authenticated"
    assert body["request_id"] == "req-1"

def test_live(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": "dev"}


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


def test_ready_fails_when_the_schema_is_behind_the_code(client, monkeypatch):
    import app.main

    monkeypatch.setattr(app.main, "EXPECTED_DB_REVISION", "9999")
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unavailable", "reason": "schema_mismatch"}


def test_each_api_request_is_logged_as_one_structured_line(client, caplog):
    import json
    import logging

    from app.core.logging import JsonFormatter

    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/api/v1/catalog/products/no-such-product", headers={"X-Request-ID": "r-9"})
        client.get("/health/live")
    [record] = [r for r in caplog.records if r.name == "app.access"]
    line = json.loads(JsonFormatter().format(record))
    assert line["path"] == "/api/v1/catalog/products/no-such-product"
    assert line["status"] == 404
    assert line["method"] == "GET"
    assert line["request_id"] == "r-9"
    assert isinstance(line["duration_ms"], float)

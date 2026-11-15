"""Two-step sign-in for staff (authenticator app codes and recovery codes)."""

import time

import pyotp
import pytest
from sqlalchemy import select

LOGIN = "/api/v1/auth/staff/login"


@pytest.fixture(autouse=True)
def _mfa_required():
    from app.core.config import get_settings

    settings = get_settings()
    settings.staff_mfa_required = True
    yield
    settings.staff_mfa_required = False


def _code(secret: str, steps_ahead: int = 0) -> str:
    return pyotp.TOTP(secret).at(time.time() + 30 * steps_ahead)


def _enrol(client, creds) -> tuple[str, list[str]]:
    """Sign in for the first time and set up the app. Returns (secret, recovery codes).

    The set-up code is the current one, so afterwards tests sign in with the next step's code."""
    resp = client.post(LOGIN, json=creds)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mfa"] == "enrol" and body["access_token"] is None
    setup = client.post(
        "/api/v1/auth/staff/mfa/setup", json={"challenge_token": body["challenge_token"]}
    ).json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    assert setup["qr_png"].startswith("data:image/png;base64,")
    resp = client.post(
        "/api/v1/auth/staff/mfa/activate",
        json={"challenge_token": body["challenge_token"], "code": _code(setup["secret"])},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]
    return setup["secret"], resp.json()["recovery_codes"]


def _challenge(client, creds) -> str:
    body = client.post(LOGIN, json=creds).json()
    assert body["mfa"] == "verify"
    return body["challenge_token"]


def _verify(client, challenge: str, code: str):
    return client.post(
        "/api/v1/auth/staff/mfa/verify", json={"challenge_token": challenge, "code": code}
    )


def test_first_sign_in_sets_up_the_app_then_codes_are_needed(client, make_staff):
    creds = make_staff("Manager")
    secret, recovery = _enrol(client, creds)
    assert len(recovery) == 10 and len(set(recovery)) == 10

    challenge = _challenge(client, creds)
    # The set-up code can't be used again (nor an older one); the next one works.
    assert _verify(client, challenge, _code(secret, -1)).status_code == 400
    resp = _verify(client, challenge, _code(secret, 1))
    assert resp.status_code == 200
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {resp.json()['access_token']}"}
    )
    assert me.json()["mfa_enabled"] is True


def test_password_alone_gives_no_session(client, make_staff):
    creds = make_staff("Manager")
    _enrol(client, creds)
    client.cookies.clear()
    resp = client.post(LOGIN, json=creds)
    assert resp.json()["access_token"] is None
    assert "set-cookie" not in resp.headers
    # The challenge is not an access token.
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {resp.json()['challenge_token']}"}
    )
    assert me.status_code == 401


def test_a_code_cannot_be_used_twice(client, make_staff):
    creds = make_staff("Manager")
    secret, _ = _enrol(client, creds)
    code = _code(secret, 1)
    assert _verify(client, _challenge(client, creds), code).status_code == 200
    resp = _verify(client, _challenge(client, creds), code)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "mfa_code_invalid"


def test_recovery_codes_work_once(client, make_staff):
    creds = make_staff("Manager")
    _, recovery = _enrol(client, creds)
    code = recovery[0].upper().replace("-", " ")  # typed loosely
    assert _verify(client, _challenge(client, creds), code).status_code == 200
    assert _verify(client, _challenge(client, creds), recovery[0]).status_code == 400


def test_wrong_codes_are_rate_limited(client, make_staff):
    creds = make_staff("Manager")
    _enrol(client, creds)
    challenge = _challenge(client, creds)
    codes = [_verify(client, challenge, "000000").status_code for _ in range(6)]
    assert codes[:5] == [400] * 5
    assert codes[5] == 429


def test_challenge_is_bound_to_its_step(client, make_staff):
    creds = make_staff("Manager")
    first = client.post(LOGIN, json=creds).json()["challenge_token"]
    # An enrol challenge can't be used to verify, and garbage is refused.
    assert _verify(client, first, "123456").status_code == 401
    assert _verify(client, "not-a-token", "123456").status_code == 401
    _enrol(client, creds)
    # Once set up, the old enrol challenge can't start a new set-up.
    resp = client.post("/api/v1/auth/staff/mfa/setup", json={"challenge_token": first})
    assert resp.status_code == 401


def test_secret_is_encrypted_at_rest(client, make_staff):
    from app.infrastructure.database import SessionLocal
    from app.modules.users.models import User

    creds = make_staff("Manager")
    secret, _ = _enrol(client, creds)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == creds["email"]))
        assert user.mfa_secret and secret not in user.mfa_secret


def test_super_admin_resets_a_lost_phone(client, make_staff):
    admin_creds = make_staff("Super Admin")
    admin_secret, _ = _enrol(client, admin_creds)
    creds = make_staff("Manager")
    _enrol(client, creds)

    token = _verify(client, _challenge(client, admin_creds), _code(admin_secret, 1)).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    staff_list = client.get("/api/v1/admin/staff", headers=headers).json()["items"]
    manager = next(s for s in staff_list if s["email"] == creds["email"])
    assert manager["mfa_enabled"] is True
    me = next(s for s in staff_list if s["email"] == admin_creds["email"])

    resp = client.post(f"/api/v1/admin/staff/{manager['id']}/mfa/reset", headers=headers)
    assert resp.status_code == 204
    assert client.post(LOGIN, json=creds).json()["mfa"] == "enrol"
    own = client.post(f"/api/v1/admin/staff/{me['id']}/mfa/reset", headers=headers)
    assert own.status_code == 422

    audit = client.get(
        "/api/v1/admin/audit-logs", params={"action": "users.mfa_reset"}, headers=headers
    )
    assert audit.json()["total"] == 1


def test_production_refuses_to_run_without_mfa(monkeypatch):
    from app.core.config import Settings

    with pytest.raises(ValueError, match="STAFF_MFA_REQUIRED"):
        Settings(
            environment="production",
            jwt_secret="x" * 40,
            mfa_encryption_key="bG9jYWwtZGV2LW9ubHktbWZhLWtleS1ub3QtcmVhbDI=",
            cookie_secure=True,
            email_backend="ses",
            staff_mfa_required=False,
            s3_access_key="",
        )


def test_cli_resets_mfa_when_no_other_super_admin_can(client, make_staff):
    from app.cli import reset_mfa

    creds = make_staff("Super Admin")
    _enrol(client, creds)
    assert reset_mfa(creds["email"].upper()) == 0
    assert client.post(LOGIN, json=creds).json()["mfa"] == "enrol"
    assert reset_mfa("nobody@example.com") == 1


def test_encryption_key_can_be_rotated(client, make_staff):
    from cryptography.fernet import Fernet

    from app.cli import rotate_mfa_key
    from app.core.config import get_settings

    creds = make_staff("Manager")
    secret, _ = _enrol(client, creds)
    settings = get_settings()
    old_key = settings.mfa_encryption_key
    new_key = Fernet.generate_key().decode()
    try:
        settings.mfa_encryption_key = f"{new_key},{old_key}"
        assert rotate_mfa_key() == 0
        settings.mfa_encryption_key = new_key  # old key removed: sign-in still works
        challenge = _challenge(client, creds)
        assert _verify(client, challenge, _code(secret, 1)).status_code == 200
    finally:
        settings.mfa_encryption_key = old_key


def test_cli_can_create_a_super_admin_with_a_password_nobody_knows(client, outbox):
    from app.cli import create_superadmin

    assert create_superadmin("Owner@Example.com", "Owner", random_password=True) == 0
    # The owner sets a password through the reset email.
    resp = client.post("/api/v1/auth/password-reset", json={"email": "owner@example.com"})
    assert resp.status_code == 202
    [email] = outbox.sent
    assert "http://localhost:4300/reset-password?token=" in email.text


def test_cli_refuses_an_email_the_sign_in_page_would_reject(client, capsys):
    from app.cli import create_superadmin

    # .local is a reserved domain: the account could never sign in, so don't create it.
    assert create_superadmin("admin@shop.local", "Admin", random_password=True) == 1
    assert "Invalid email" in capsys.readouterr().err
    resp = client.post(
        "/api/v1/auth/staff/login", json={"email": "admin@shop.local", "password": "x" * 12}
    )
    assert resp.status_code == 422

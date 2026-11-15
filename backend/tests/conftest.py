"""Tests run against a real PostgreSQL database (never SQLite), migrated with Alembic.

Set TEST_DATABASE_URL to point elsewhere; the default matches docker-compose and CI.
"""

import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/ecommerce_test",
)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ENVIRONMENT"] = "test"
# Most tests sign staff straight in; test_staff_mfa.py turns two-step sign-in on.
os.environ["STAFF_MFA_REQUIRED"] = "false"


def _recreate_database(url: str) -> None:
    parsed = make_url(url)
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{parsed.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> Iterator[None]:
    from alembic import command
    from alembic.config import Config

    _recreate_database(TEST_DB_URL)
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    """Keep seeded roles and permissions; remove everything users created."""
    yield
    from app.core.rate_limit import login_limiter
    from app.infrastructure.database import engine
    from app.modules.access_control.permissions import DEFAULT_ROLE_GRANTS

    login_limiter.reset()
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE users, refresh_tokens, password_reset_tokens, user_roles, audit_logs, "
                "categories, brands, products, product_skus, product_attributes, product_media, "
                "addresses, carts, "
                "cart_items, orders, order_items, order_status_events CASCADE"
            )
        )
        # Put roles back to the seeded defaults: drop custom roles, reset grants.
        conn.execute(text("DELETE FROM roles WHERE NOT is_system"))
        conn.execute(text("DELETE FROM role_permissions"))
        for role_name, keys in DEFAULT_ROLE_GRANTS.items():
            conn.execute(
                text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "SELECT r.id, p.id FROM roles r JOIN permissions p ON p.key = ANY(:keys) "
                    "WHERE r.name = :name"
                ),
                {"name": role_name, "keys": keys},
            )


class FakeStorage:
    """In-memory stand-in for S3 so tests never touch the network."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def public_url(self, key: str) -> str:
        return f"https://cdn.test/{key}"

    def get(self, key: str) -> bytes:
        return self.objects[key][0]


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def files() -> FakeStorage:
    """Stand-in for the private bucket (courier exports and imports)."""
    return FakeStorage()


class Outbox:
    """Collects emails instead of sending them."""

    def __init__(self) -> None:
        self.sent: list = []

    def send(self, email) -> None:
        self.sent.append(email)


@pytest.fixture
def outbox() -> Outbox:
    return Outbox()


@pytest.fixture
def client(storage: FakeStorage, files: FakeStorage, outbox: Outbox) -> Iterator[TestClient]:
    from app.infrastructure.email import get_email_sender
    from app.infrastructure.storage import get_file_store, get_storage
    from app.main import app

    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_file_store] = lambda: files
    app.dependency_overrides[get_email_sender] = lambda: outbox
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_staff() -> Callable[..., dict[str, str]]:
    """Create a staff user holding the given roles; returns its credentials."""
    from app.core.security import hash_password
    from app.infrastructure.database import SessionLocal
    from app.modules.access_control.models import Role
    from app.modules.users.models import User, UserType

    counter = {"n": 0}

    def factory(*role_names: str, password: str = "staff-password-123") -> dict[str, str]:
        counter["n"] += 1
        email = f"staff{counter['n']}@example.com"
        with SessionLocal() as db:
            roles = list(db.scalars(select(Role).where(Role.name.in_(role_names))).all())
            db.add(
                User(
                    email=email,
                    full_name=f"Staff {counter['n']}",
                    password_hash=hash_password(password),
                    user_type=UserType.STAFF,
                    roles=roles,
                )
            )
            db.commit()
        return {"email": email, "password": password}

    return factory


@pytest.fixture
def buyer_token(client) -> Callable[..., str]:
    counter = {"n": 0}

    def login(name: str = "Buyer") -> str:
        counter["n"] += 1
        creds = {"email": f"buyer{counter['n']}@example.com", "password": "buyer-password-1"}
        client.post("/api/v1/auth/register", json={**creds, "full_name": f"{name} {counter['n']}"})
        resp = client.post("/api/v1/auth/login", json=creds)
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return login


@pytest.fixture
def staff_token(client, make_staff) -> Callable[..., str]:
    def login(*role_names: str) -> str:
        creds = make_staff(*role_names)
        resp = client.post("/api/v1/auth/staff/login", json=creds)
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return login

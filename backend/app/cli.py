"""Operational commands. Usage:

    python -m app.cli create-superadmin --email you@example.com --name "Your Name"

The password is read from the SUPERADMIN_PASSWORD environment variable or prompted for,
so it never appears in shell history.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.security import hash_password
from app.infrastructure.database import SessionLocal
from app.modules.access_control.models import Role
from app.modules.access_control.permissions import SUPER_ADMIN
from app.modules.users.models import User, UserType


def create_superadmin(email: str, name: str) -> int:
    password = os.environ.get("SUPERADMIN_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.name == SUPER_ADMIN))
        if role is None:
            print("Super Admin role missing. Run `alembic upgrade head` first.", file=sys.stderr)
            return 1
        normalised = email.strip().lower()
        if db.scalar(select(User).where(User.email == normalised)):
            print(f"A user with email {normalised} already exists.", file=sys.stderr)
            return 1
        db.add(
            User(
                email=normalised,
                full_name=name,
                password_hash=hash_password(password),
                user_type=UserType.STAFF,
                roles=[role],
            )
        )
        db.commit()
    print(f"Created Super Admin {normalised}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("create-superadmin")
    cmd.add_argument("--email", required=True)
    cmd.add_argument("--name", required=True)
    args = parser.parse_args()
    if args.command == "create-superadmin":
        return create_superadmin(args.email, args.name)
    return 1


if __name__ == "__main__":
    sys.exit(main())

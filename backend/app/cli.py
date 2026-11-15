"""Operational commands. Usage:

    python -m app.cli create-superadmin --email you@example.com --name "Your Name"
    python -m app.cli reset-mfa --email someone@example.com

reset-mfa is for a staff member who lost their phone when no other Super Admin can reset it in the
admin portal: it removes their authenticator app and signs them out, and they set up a new app at
their next sign-in.

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


def reset_mfa(email: str) -> int:
    from datetime import UTC, datetime

    from sqlalchemy import update

    from app.modules.audit import service as audit
    from app.modules.auth import mfa
    from app.modules.auth.models import RefreshToken

    with SessionLocal() as db:
        normalised = email.strip().lower()
        user = db.scalar(
            select(User).where(User.email == normalised, User.user_type == UserType.STAFF)
        )
        if user is None:
            print(f"No staff member with email {normalised}.", file=sys.stderr)
            return 1
        mfa.turn_off(db, user)
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        audit.record(
            db, "users.mfa_reset", actor_id=None, entity_type="user", entity_id=str(user.id)
        )
        db.commit()
    print(f"Two-step sign-in reset for {normalised}. They set up a new app at their next sign-in.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("create-superadmin")
    cmd.add_argument("--email", required=True)
    cmd.add_argument("--name", required=True)
    reset = sub.add_parser("reset-mfa")
    reset.add_argument("--email", required=True)
    args = parser.parse_args()
    if args.command == "create-superadmin":
        return create_superadmin(args.email, args.name)
    if args.command == "reset-mfa":
        return reset_mfa(args.email)
    return 1


if __name__ == "__main__":
    sys.exit(main())

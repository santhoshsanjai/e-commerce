"""Operational commands. Usage:

    python -m app.cli create-superadmin --email you@example.com --name "Your Name"
    python -m app.cli reset-mfa --email someone@example.com
    python -m app.cli rotate-mfa-key
    python -m app.cli seed-sample-products

reset-mfa is for a staff member who lost their phone when no other Super Admin can reset it in the
admin portal: it removes their authenticator app and signs them out, and they set up a new app at
their next sign-in.

The password is read from the SUPERADMIN_PASSWORD environment variable or prompted for,
so it never appears in shell history. On AWS, where there is no prompt, use --random-password:
the account gets a password nobody knows, and its owner sets their own with "Forgot your
password?" on the admin sign-in page.

seed-sample-products adds 50 published demo products in 5 categories, each with a picture, for
local and staging shops. Running it again adds nothing new. It refuses to run in production.
"""

import argparse
import getpass
import os
import secrets
import sys

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.security import hash_password
from app.infrastructure.database import SessionLocal
from app.modules.access_control.models import Role
from app.modules.access_control.permissions import SUPER_ADMIN
from app.modules.users.models import User, UserType


def create_superadmin(email: str, name: str, random_password: bool = False) -> int:
    if random_password:
        password = secrets.token_urlsafe(32)
    else:
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
    if random_password:
        print('Set the password with "Forgot your password?" on the admin sign-in page.')
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


def rotate_mfa_key() -> int:
    """Re-encrypt authenticator secrets with the first key in MFA_ENCRYPTION_KEY."""
    from app.modules.auth import mfa

    with SessionLocal() as db:
        count = mfa.reencrypt_all(db)
    print(f"Re-encrypted two-step sign-in secrets for {count} account(s).")
    return 0


def seed_sample_products() -> int:
    from app.core.config import get_settings
    from app.infrastructure.storage import get_storage
    from app.seed.products import seed

    if get_settings().environment == "production":
        print("Sample products are for local and staging shops only.", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        added, present = seed(db, get_storage())
    print(f"Added {added} sample product(s); {present} were already there.")
    return 0


def send_emails() -> int:
    """Send queued order emails (retrying failed ones) and delete sent ones older than 30 days.
    Runs every few minutes as a scheduled task."""
    from app.infrastructure.email import get_email_sender
    from app.modules.notifications.service import deliver_pending, purge_sent

    sent = deliver_pending(get_email_sender(), limit=500)
    with SessionLocal() as db:
        purged = purge_sent(db)
    print(f"Sent {sent} email(s); removed {purged} old sent email(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("create-superadmin")
    cmd.add_argument("--email", required=True)
    cmd.add_argument("--name", required=True)
    cmd.add_argument("--random-password", action="store_true")
    reset = sub.add_parser("reset-mfa")
    reset.add_argument("--email", required=True)
    sub.add_parser("rotate-mfa-key")
    sub.add_parser("seed-sample-products")
    sub.add_parser("send-emails")
    args = parser.parse_args()
    if args.command == "create-superadmin":
        return create_superadmin(args.email, args.name, args.random_password)
    if args.command == "reset-mfa":
        return reset_mfa(args.email)
    if args.command == "rotate-mfa-key":
        return rotate_mfa_key()
    if args.command == "seed-sample-products":
        return seed_sample_products()
    if args.command == "send-emails":
        return send_emails()
    return 1


if __name__ == "__main__":
    sys.exit(main())

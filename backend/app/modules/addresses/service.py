import uuid

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.addresses.models import Address
from app.modules.addresses.schemas import AddressIn
from app.modules.users.models import User

MAX_ADDRESSES = 20


def list_addresses(db: Session, user: User) -> list[Address]:
    return list(
        db.scalars(
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.is_default.desc(), Address.created_at)
        ).all()
    )


def get_owned(db: Session, user: User, address_id: uuid.UUID) -> Address:
    """Fetch an address only if the user owns it. Others get 404, never 403 (no IDOR probing)."""
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == user.id))
    if address is None:
        raise AppError("address_not_found", "Address not found", status.HTTP_404_NOT_FOUND)
    return address


def _clear_default(db: Session, user: User) -> None:
    db.execute(update(Address).where(Address.user_id == user.id).values(is_default=False))


def create_address(db: Session, user: User, data: AddressIn) -> Address:
    existing = list_addresses(db, user)
    if len(existing) >= MAX_ADDRESSES:
        raise AppError("too_many_addresses", f"You can save up to {MAX_ADDRESSES} addresses")
    make_default = data.is_default or not existing
    if make_default:
        _clear_default(db, user)
    address = Address(
        user_id=user.id, **data.model_dump(exclude={"is_default"}), is_default=make_default
    )
    db.add(address)
    db.commit()
    return address


def update_address(db: Session, user: User, address_id: uuid.UUID, data: AddressIn) -> Address:
    address = get_owned(db, user, address_id)
    if data.is_default and not address.is_default:
        _clear_default(db, user)
    for field, value in data.model_dump().items():
        if field == "is_default" and not value and address.is_default:
            continue  # keep one default; set another address as default instead
        setattr(address, field, value)
    db.commit()
    return address


def delete_address(db: Session, user: User, address_id: uuid.UUID) -> None:
    address = get_owned(db, user, address_id)
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:
        replacement = db.scalar(
            select(Address).where(Address.user_id == user.id).order_by(Address.created_at)
        )
        if replacement:
            replacement.is_default = True
    db.commit()

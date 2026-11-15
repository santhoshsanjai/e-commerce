import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentBuyer, DbSession
from app.infrastructure.storage import ObjectStorage, get_storage
from app.modules.cart import service
from app.modules.cart.schemas import CartItemAdd, CartItemUpdate, CartOut

router = APIRouter(prefix="/cart", tags=["buyer: cart"])
Storage = Annotated[ObjectStorage, Depends(get_storage)]


@router.get("")
def get_cart(db: DbSession, storage: Storage, user: CurrentBuyer) -> CartOut:
    cart = service.get_or_create_cart(db, user)
    db.commit()
    return service.to_out(db, cart, storage)


@router.post("/items")
def add_item(data: CartItemAdd, db: DbSession, storage: Storage, user: CurrentBuyer) -> CartOut:
    return service.to_out(db, service.add_item(db, user, data), storage)


@router.patch("/items/{sku_id}")
def update_item(
    sku_id: uuid.UUID, data: CartItemUpdate, db: DbSession, storage: Storage, user: CurrentBuyer
) -> CartOut:
    return service.to_out(db, service.set_quantity(db, user, sku_id, data.qty), storage)


@router.delete("/items/{sku_id}")
def remove_item(sku_id: uuid.UUID, db: DbSession, storage: Storage, user: CurrentBuyer) -> CartOut:
    return service.to_out(db, service.remove_item(db, user, sku_id), storage)

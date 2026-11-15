import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentBuyer, DbSession
from app.modules.addresses import service
from app.modules.addresses.schemas import AddressIn, AddressOut

router = APIRouter(prefix="/me/addresses", tags=["buyer: addresses"])


@router.get("")
def list_addresses(db: DbSession, user: CurrentBuyer) -> list[AddressOut]:
    return [AddressOut.model_validate(a) for a in service.list_addresses(db, user)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_address(data: AddressIn, db: DbSession, user: CurrentBuyer) -> AddressOut:
    return AddressOut.model_validate(service.create_address(db, user, data))


@router.put("/{address_id}")
def update_address(
    address_id: uuid.UUID, data: AddressIn, db: DbSession, user: CurrentBuyer
) -> AddressOut:
    return AddressOut.model_validate(service.update_address(db, user, address_id, data))


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(address_id: uuid.UUID, db: DbSession, user: CurrentBuyer) -> None:
    service.delete_address(db, user, address_id)

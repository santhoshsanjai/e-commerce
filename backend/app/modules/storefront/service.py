import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit import service as audit
from app.modules.storefront.models import StorefrontSettings
from app.modules.storefront.schemas import Storefront, StorefrontUpdate

DEFAULT = Storefront(store_name="Shop", announcement="", colors={})


def _out(row: StorefrontSettings | None) -> Storefront:
    if row is None:
        return DEFAULT
    return Storefront(store_name=row.store_name, announcement=row.announcement, colors=row.colors)


def get(db: Session) -> Storefront:
    return _out(db.get(StorefrontSettings, 1))


def update(
    db: Session, data: StorefrontUpdate, *, actor_id: uuid.UUID, request: Request
) -> Storefront:
    row = db.get(StorefrontSettings, 1)
    before = _out(row).model_dump()
    if row is None:
        row = StorefrontSettings(id=1)
        db.add(row)
    row.store_name = data.store_name
    row.announcement = data.announcement
    row.colors = data.colors
    row.updated_by = actor_id
    audit.record(
        db,
        "storefront.updated",
        actor_id=actor_id,
        request=request,
        entity_type="storefront",
        entity_id="1",
        before=before,
        after=data.model_dump(),
    )
    db.commit()
    return _out(row)

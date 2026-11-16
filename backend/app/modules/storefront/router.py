from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.core.dependencies import DbSession, require_permission
from app.modules.storefront import service
from app.modules.storefront.schemas import Storefront, StorefrontUpdate
from app.modules.users.models import User

public_router = APIRouter(tags=["storefront"])
admin_router = APIRouter(prefix="/admin", tags=["admin: storefront"])

CanManage = Annotated[User, Depends(require_permission("settings.manage"))]


@public_router.get("/storefront")
def storefront(db: DbSession, response: Response) -> Storefront:
    """Shop name, announcement and colour overrides. Public: both apps read it at start-up."""
    response.headers["Cache-Control"] = "public, max-age=60"
    return service.get(db)


@admin_router.get("/storefront")
def admin_storefront(db: DbSession, _: CanManage) -> Storefront:
    return service.get(db)


@admin_router.put("/storefront")
def update_storefront(
    data: StorefrontUpdate, db: DbSession, user: CanManage, request: Request
) -> Storefront:
    return service.update(db, data, actor_id=user.id, request=request)

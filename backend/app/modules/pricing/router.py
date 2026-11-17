from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import DbSession, require_permission
from app.modules.pricing import service
from app.modules.pricing.schemas import Charges, ChargesUpdate
from app.modules.users.models import User

router = APIRouter(prefix="/admin/charges", tags=["admin: delivery and GST"])

CanManage = Annotated[User, Depends(require_permission("settings.manage"))]


@router.get("")
def get_charges(db: DbSession, _: CanManage) -> Charges:
    return service.get(db)


@router.put("")
def update_charges(
    data: ChargesUpdate, db: DbSession, user: CanManage, request: Request
) -> Charges:
    """Change the delivery charge and GST rules. Orders already placed keep their amounts."""
    return service.update(db, data, actor_id=user.id, request=request)

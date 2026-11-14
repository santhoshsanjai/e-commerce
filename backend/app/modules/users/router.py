from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import DbSession, require_permission
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import StaffCreate, StaffOut
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/admin/staff", tags=["admin: staff"])


@router.get("")
def list_staff(
    db: DbSession,
    _: Annotated[User, Depends(require_permission("users.view"))],
    params: Annotated[PageParams, Depends(page_params)],
) -> Page[StaffOut]:
    return service.list_staff(db, params)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_staff(
    data: StaffCreate,
    request: Request,
    db: DbSession,
    actor: Annotated[User, Depends(require_permission("users.manage"))],
) -> StaffOut:
    return service.to_staff_out(service.create_staff(db, data, actor, request))

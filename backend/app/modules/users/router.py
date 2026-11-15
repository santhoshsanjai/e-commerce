import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.dependencies import DbSession, require_permission
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import (
    PasswordReset,
    StaffCreate,
    StaffOut,
    StaffStatus,
    StaffUpdate,
)
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/admin/staff", tags=["admin: staff"])

CanView = Annotated[User, Depends(require_permission("users.view"))]
CanManage = Annotated[User, Depends(require_permission("users.manage"))]


@router.get("")
def list_staff(
    db: DbSession,
    _: CanView,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    role_id: uuid.UUID | None = None,
    status_filter: Annotated[StaffStatus | None, Query(alias="status")] = None,
) -> Page[StaffOut]:
    return service.list_staff(db, params, q=q, role_id=role_id, status_filter=status_filter)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_staff(data: StaffCreate, request: Request, db: DbSession, actor: CanManage) -> StaffOut:
    return service.to_staff_out(service.create_staff(db, data, actor, request))


@router.get("/{staff_id}")
def get_staff(staff_id: uuid.UUID, db: DbSession, _: CanView) -> StaffOut:
    return service.to_staff_out(service.get_staff(db, staff_id))


@router.patch("/{staff_id}")
def update_staff(
    staff_id: uuid.UUID, data: StaffUpdate, request: Request, db: DbSession, actor: CanManage
) -> StaffOut:
    return service.to_staff_out(service.update_staff(db, staff_id, data, actor, request))


@router.post("/{staff_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    staff_id: uuid.UUID, data: PasswordReset, request: Request, db: DbSession, actor: CanManage
) -> Response:
    service.reset_password(db, staff_id, data.password, actor, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{staff_id}/mfa/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_mfa(staff_id: uuid.UUID, request: Request, db: DbSession, actor: CanManage) -> Response:
    """Remove a staff member's authenticator app (lost phone); they set up a new one at sign-in."""
    service.reset_mfa(db, staff_id, actor, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

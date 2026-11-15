import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select

from app.core.dependencies import DbSession, require_permission
from app.modules.access_control import service
from app.modules.access_control.models import Permission
from app.modules.access_control.schemas import PermissionOut, RoleCreate, RoleOut, RoleUpdate
from app.modules.users.models import User

router = APIRouter(prefix="/admin", tags=["admin: access control"])

CanViewRoles = Annotated[User, Depends(require_permission("roles.view"))]
CanManageRoles = Annotated[User, Depends(require_permission("roles.manage"))]


@router.get("/roles")
def list_roles(db: DbSession, _: CanViewRoles) -> list[RoleOut]:
    return service.list_roles(db)


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(
    data: RoleCreate, request: Request, db: DbSession, actor: CanManageRoles
) -> RoleOut:
    return service.role_out(db, service.create_role(db, data, actor, request))


@router.patch("/roles/{role_id}")
def update_role(
    role_id: uuid.UUID, data: RoleUpdate, request: Request, db: DbSession, actor: CanManageRoles
) -> RoleOut:
    return service.role_out(db, service.update_role(db, role_id, data, actor, request))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: uuid.UUID, request: Request, db: DbSession, actor: CanManageRoles
) -> Response:
    service.delete_role(db, role_id, actor, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/permissions")
def list_permissions(db: DbSession, _: CanViewRoles) -> list[PermissionOut]:
    perms = db.scalars(select(Permission).order_by(Permission.key)).all()
    return [PermissionOut.model_validate(p) for p in perms]

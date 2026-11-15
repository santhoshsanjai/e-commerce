from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.dependencies import DbSession, require_permission
from app.modules.access_control.models import Permission, Role
from app.modules.access_control.schemas import PermissionOut, RoleOut
from app.modules.users.models import User

router = APIRouter(prefix="/admin", tags=["admin: access control"])

CanViewRoles = Annotated[User, Depends(require_permission("roles.view"))]


@router.get("/roles")
def list_roles(db: DbSession, _: CanViewRoles) -> list[RoleOut]:
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [
        RoleOut(
            id=r.id,
            name=r.name,
            description=r.description,
            is_system=r.is_system,
            permissions=sorted(p.key for p in r.permissions),
        )
        for r in roles
    ]


@router.get("/permissions")
def list_permissions(db: DbSession, _: CanViewRoles) -> list[PermissionOut]:
    perms = db.scalars(select(Permission).order_by(Permission.key)).all()
    return [PermissionOut.model_validate(p) for p in perms]

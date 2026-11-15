import uuid
from typing import Any

from fastapi import Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, PermissionDenied
from app.modules.access_control.models import Permission, Role, user_roles
from app.modules.access_control.permissions import SUPER_ADMIN
from app.modules.access_control.schemas import RoleCreate, RoleOut, RoleUpdate
from app.modules.audit import service as audit
from app.modules.users.models import User, UserType


def permissions_for(user: User) -> set[str]:
    """Union of permissions across all of the user's roles. Buyers never hold admin permissions."""
    if user.user_type is not UserType.STAFF:
        return set()
    return {perm.key for role in user.roles for perm in role.permissions}


def _user_counts(db: Session) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(user_roles.c.role_id, func.count())
        .join(User, User.id == user_roles.c.user_id)
        .group_by(user_roles.c.role_id)
    ).all()
    return {role_id: count for role_id, count in rows}


def to_role_out(role: Role, user_count: int) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=sorted(p.key for p in role.permissions),
        user_count=user_count,
    )


def list_roles(db: Session) -> list[RoleOut]:
    counts = _user_counts(db)
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [to_role_out(r, counts.get(r.id, 0)) for r in roles]


def role_out(db: Session, role: Role) -> RoleOut:
    return to_role_out(role, _user_counts(db).get(role.id, 0))


def _get_role(db: Session, role_id: uuid.UUID) -> Role:
    role = db.scalar(select(Role).where(Role.id == role_id).with_for_update())
    if role is None:
        raise AppError("role_not_found", "Role not found", status.HTTP_404_NOT_FOUND)
    return role


def _load_permissions(db: Session, keys: list[str]) -> list[Permission]:
    wanted = set(keys)
    perms = list(db.scalars(select(Permission).where(Permission.key.in_(wanted))).all())
    unknown = wanted - {p.key for p in perms}
    if unknown:
        raise AppError(
            "unknown_permission",
            "One or more permissions do not exist",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={"unknown": sorted(unknown)},
        )
    return perms


def _check_no_escalation(actor: User, granted: set[str]) -> None:
    """Nobody can hand out a permission they don't hold themselves."""
    missing = granted - permissions_for(actor)
    if missing:
        raise PermissionDenied(
            "You can only grant permissions you hold yourself: " + ", ".join(sorted(missing))
        )


def _name_taken() -> AppError:
    return AppError(
        "role_name_taken", "A role with this name already exists", status.HTTP_409_CONFLICT
    )


def create_role(db: Session, data: RoleCreate, actor: User, request: Request) -> Role:
    perms = _load_permissions(db, data.permissions)
    _check_no_escalation(actor, {p.key for p in perms})
    role = Role(
        name=data.name.strip(),
        description=data.description.strip(),
        is_system=False,
        permissions=perms,
    )
    db.add(role)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _name_taken() from exc
    audit.record(
        db,
        "roles.created",
        actor_id=actor.id,
        request=request,
        entity_type="role",
        entity_id=str(role.id),
        after={"name": role.name, "permissions": sorted(p.key for p in perms)},
    )
    db.commit()
    return role


def update_role(
    db: Session, role_id: uuid.UUID, data: RoleUpdate, actor: User, request: Request
) -> Role:
    role = _get_role(db, role_id)
    if role.name == SUPER_ADMIN:
        raise AppError(
            "super_admin_locked",
            "The Super Admin role always has every permission and can't be changed",
            status.HTTP_409_CONFLICT,
        )
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}

    if data.name is not None and data.name.strip() != role.name:
        if role.is_system:
            raise AppError(
                "system_role", "Built-in roles can't be renamed", status.HTTP_409_CONFLICT
            )
        before["name"], after["name"] = role.name, data.name.strip()
        role.name = data.name.strip()
    if data.description is not None and data.description.strip() != role.description:
        before["description"], after["description"] = role.description, data.description.strip()
        role.description = data.description.strip()
    if data.permissions is not None:
        perms = _load_permissions(db, data.permissions)
        old = {p.key for p in role.permissions}
        new = {p.key for p in perms}
        _check_no_escalation(actor, new - old)
        if old != new:
            before["permissions"], after["permissions"] = sorted(old), sorted(new)
            role.permissions = perms

    if after:
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise _name_taken() from exc
        audit.record(
            db,
            "roles.updated",
            actor_id=actor.id,
            request=request,
            entity_type="role",
            entity_id=str(role.id),
            before=before,
            after=after,
        )
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: uuid.UUID, actor: User, request: Request) -> None:
    role = _get_role(db, role_id)
    if role.is_system:
        raise AppError("system_role", "Built-in roles can't be deleted", status.HTTP_409_CONFLICT)
    in_use = _user_counts(db).get(role.id, 0)
    if in_use:
        raise AppError(
            "role_in_use",
            f"{in_use} staff member(s) still have this role. Move them to another role first.",
            status.HTTP_409_CONFLICT,
            details={"user_count": in_use},
        )
    audit.record(
        db,
        "roles.deleted",
        actor_id=actor.id,
        request=request,
        entity_type="role",
        entity_id=str(role.id),
        before={"name": role.name, "permissions": sorted(p.key for p in role.permissions)},
    )
    db.delete(role)
    db.commit()

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, PermissionDenied
from app.core.security import hash_password
from app.modules.access_control.models import Role, user_roles
from app.modules.access_control.permissions import SUPER_ADMIN
from app.modules.audit import service as audit
from app.modules.auth import mfa
from app.modules.auth.models import RefreshToken
from app.modules.users.models import User, UserType
from app.modules.users.schemas import StaffCreate, StaffOut, StaffStatus, StaffUpdate
from app.shared.pagination import Page, PageParams


def to_staff_out(user: User) -> StaffOut:
    roles = sorted(user.roles, key=lambda r: r.name)
    return StaffOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        roles=[r.name for r in roles],
        role_ids=[r.id for r in roles],
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        mfa_enabled=user.mfa_enabled,
    )


def list_staff(
    db: Session,
    params: PageParams,
    *,
    q: str | None = None,
    role_id: uuid.UUID | None = None,
    status_filter: StaffStatus | None = None,
) -> Page[StaffOut]:
    base = select(User).where(User.user_type == UserType.STAFF)
    if q and q.strip():
        term = f"%{q.strip()}%"
        base = base.where(or_(User.full_name.ilike(term), User.email.ilike(term)))
    if role_id is not None:
        base = base.where(
            User.id.in_(select(user_roles.c.user_id).where(user_roles.c.role_id == role_id))
        )
    if status_filter is not None:
        base = base.where(User.is_active.is_(status_filter is StaffStatus.ACTIVE))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    users = db.scalars(
        base.order_by(User.created_at.desc(), User.id).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(
        items=[to_staff_out(u) for u in users],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def _is_super_admin(user: User) -> bool:
    return any(r.name == SUPER_ADMIN for r in user.roles)


def _load_roles(db: Session, role_ids: list[uuid.UUID]) -> list[Role]:
    roles = list(db.scalars(select(Role).where(Role.id.in_(role_ids))).all())
    if len(roles) != len(set(role_ids)):
        raise AppError(
            "unknown_role", "One or more roles do not exist", status.HTTP_422_UNPROCESSABLE_CONTENT
        )
    return roles


def get_staff(db: Session, staff_id: uuid.UUID, *, lock: bool = False) -> User:
    query = select(User).where(User.id == staff_id, User.user_type == UserType.STAFF)
    if lock:
        query = query.with_for_update()
    user = db.scalar(query)
    if user is None:
        raise AppError("staff_not_found", "Staff member not found", status.HTTP_404_NOT_FOUND)
    return user


def create_staff(db: Session, data: StaffCreate, actor: User, request: Request) -> User:
    roles = _load_roles(db, data.role_ids)
    if any(r.name == SUPER_ADMIN for r in roles) and not _is_super_admin(actor):
        raise PermissionDenied("Only a Super Admin can grant the Super Admin role")
    user = User(
        email=data.email.strip().lower(),
        full_name=data.full_name.strip(),
        phone=data.phone,
        password_hash=hash_password(data.password),
        user_type=UserType.STAFF,
        roles=roles,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "email_taken", "An account with this email already exists", status.HTTP_409_CONFLICT
        ) from exc
    audit.record(
        db,
        "users.staff_created",
        actor_id=actor.id,
        request=request,
        entity_type="user",
        entity_id=str(user.id),
        after={"email": user.email, "roles": sorted(r.name for r in roles)},
    )
    db.commit()
    return user


def _guard_target(actor: User, target: User) -> None:
    if _is_super_admin(target) and not _is_super_admin(actor):
        raise PermissionDenied("Only a Super Admin can change a Super Admin's account")


def _revoke_sessions(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


def _ensure_another_super_admin(db: Session, target: User) -> None:
    """Refuse a change that would leave no active Super Admin.

    Locks every active Super Admin row first, so two Super Admins deactivating each other at the
    same moment cannot both succeed.
    """
    super_ids = select(user_roles.c.user_id).join(Role, Role.id == user_roles.c.role_id)
    rows = db.scalars(
        select(User.id)
        .where(
            User.id.in_(super_ids.where(Role.name == SUPER_ADMIN)),
            User.is_active.is_(True),
            User.user_type == UserType.STAFF,
        )
        .order_by(User.id)
        .with_for_update(of=User)
    ).all()
    if not any(uid != target.id for uid in rows):
        raise AppError(
            "last_super_admin",
            "There must always be at least one active Super Admin",
            status.HTTP_409_CONFLICT,
        )


def update_staff(
    db: Session, staff_id: uuid.UUID, data: StaffUpdate, actor: User, request: Request
) -> User:
    target = get_staff(db, staff_id, lock=True)
    _guard_target(actor, target)
    changes = data.model_dump(exclude_unset=True)
    if target.id == actor.id and ("role_ids" in changes or "is_active" in changes):
        raise AppError(
            "cannot_change_own_access",
            "You can't change your own roles or deactivate yourself. Ask another administrator.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    before: dict[str, Any] = {}
    after: dict[str, Any] = {}

    def note(field: str, old: Any, new: Any) -> None:
        if old != new:
            before[field] = old
            after[field] = new

    if data.full_name is not None:
        note("full_name", target.full_name, data.full_name.strip())
        target.full_name = data.full_name.strip()
    if "phone" in changes:
        phone = data.phone.strip() if data.phone else None
        note("phone", target.phone, phone or None)
        target.phone = phone or None

    was_super = _is_super_admin(target)
    if data.role_ids is not None:
        roles = _load_roles(db, data.role_ids)
        grants_super = any(r.name == SUPER_ADMIN for r in roles)
        if grants_super and not _is_super_admin(actor):
            raise PermissionDenied("Only a Super Admin can grant the Super Admin role")
        if was_super and not grants_super and target.is_active:
            _ensure_another_super_admin(db, target)
        note("roles", sorted(r.name for r in target.roles), sorted(r.name for r in roles))
        target.roles = roles

    if data.is_active is not None and data.is_active != target.is_active:
        if not data.is_active and _is_super_admin(target):
            _ensure_another_super_admin(db, target)
        note("is_active", target.is_active, data.is_active)
        target.is_active = data.is_active
        if not data.is_active:
            # Access tokens already stop working: every request re-checks is_active.
            _revoke_sessions(db, target.id)

    if after:
        action = "users.staff_updated"
        if after.keys() == {"is_active"}:
            action = "users.staff_activated" if data.is_active else "users.staff_deactivated"
        audit.record(
            db,
            action,
            actor_id=actor.id,
            request=request,
            entity_type="user",
            entity_id=str(target.id),
            before=before,
            after=after,
        )
    db.commit()
    db.refresh(target)
    return target


def reset_password(
    db: Session, staff_id: uuid.UUID, password: str, actor: User, request: Request
) -> None:
    target = get_staff(db, staff_id, lock=True)
    _guard_target(actor, target)
    if target.id == actor.id:
        raise AppError(
            "cannot_reset_own_password",
            "Use “Change password” to change your own password.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    target.password_hash = hash_password(password)
    _revoke_sessions(db, target.id)
    audit.record(
        db,
        "users.password_reset",
        actor_id=actor.id,
        request=request,
        entity_type="user",
        entity_id=str(target.id),
    )
    db.commit()


def reset_mfa(db: Session, staff_id: uuid.UUID, actor: User, request: Request) -> None:
    """For a lost phone: remove the person's authenticator app and recovery codes and sign them
    out. They set up a new app at their next sign-in."""
    target = get_staff(db, staff_id, lock=True)
    _guard_target(actor, target)
    if target.id == actor.id:
        raise AppError(
            "cannot_reset_own_mfa",
            "Ask another Super Admin to reset your two-step sign-in.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    mfa.turn_off(db, target)
    _revoke_sessions(db, target.id)
    audit.record(
        db,
        "users.mfa_reset",
        actor_id=actor.id,
        request=request,
        entity_type="user",
        entity_id=str(target.id),
    )
    db.commit()

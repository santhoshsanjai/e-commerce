from fastapi import Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, PermissionDenied
from app.core.security import hash_password
from app.modules.access_control.models import Role
from app.modules.access_control.permissions import SUPER_ADMIN
from app.modules.audit import service as audit
from app.modules.users.models import User, UserType
from app.modules.users.schemas import StaffCreate, StaffOut
from app.shared.pagination import Page, PageParams


def to_staff_out(user: User) -> StaffOut:
    return StaffOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        roles=sorted(r.name for r in user.roles),
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def list_staff(db: Session, params: PageParams) -> Page[StaffOut]:
    base = select(User).where(User.user_type == UserType.STAFF)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    users = db.scalars(
        base.order_by(User.created_at.desc()).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(
        items=[to_staff_out(u) for u in users],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def create_staff(db: Session, data: StaffCreate, actor: User, request: Request) -> User:
    roles = list(db.scalars(select(Role).where(Role.id.in_(data.role_ids))).all())
    if len(roles) != len(set(data.role_ids)):
        raise AppError(
            "unknown_role", "One or more roles do not exist", status.HTTP_422_UNPROCESSABLE_CONTENT
        )
    actor_roles = {r.name for r in actor.roles}
    if any(r.name == SUPER_ADMIN for r in roles) and SUPER_ADMIN not in actor_roles:
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

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app.core.dependencies import DbSession, require_permission
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditEntryOut
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams, page_params
from app.shared.timezones import IST

router = APIRouter(prefix="/admin/audit-logs", tags=["admin: audit"])

CanViewAudit = Annotated[User, Depends(require_permission("audit_logs.view"))]


@router.get("/actions")
def actions(db: DbSession, _: CanViewAudit) -> list[str]:
    """Action names that occur in the log, for the filter dropdown."""
    return list(db.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action)))


@router.get("")
def list_entries(
    db: DbSession,
    _: CanViewAudit,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[
        str | None, Query(max_length=200, description="Staff name or email, or record id")
    ] = None,
    action: Annotated[str | None, Query(max_length=100)] = None,
    entity_type: Annotated[str | None, Query(max_length=100)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[AuditEntryOut]:
    """Newest first. Dates are Indian calendar days."""
    query = select(AuditLog, User.full_name, User.email).outerjoin(
        User, User.id == AuditLog.actor_id
    )
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            or_(User.full_name.ilike(like), User.email.ilike(like), AuditLog.entity_id == q.strip())
        )
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if date_from:
        query = query.where(AuditLog.occurred_at >= datetime.combine(date_from, time.min, IST))
    if date_to:
        query = query.where(
            AuditLog.occurred_at < datetime.combine(date_to + timedelta(days=1), time.min, IST)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(AuditLog.occurred_at.desc(), AuditLog.id)
        .offset(params.offset)
        .limit(params.page_size)
    ).all()
    items = [
        AuditEntryOut(
            id=e.id,
            occurred_at=e.occurred_at,
            action=e.action,
            actor_name=name,
            actor_email=email,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            before=e.before,
            after=e.after,
            ip=e.ip,
            request_id=e.request_id,
        )
        for e, name, email in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)

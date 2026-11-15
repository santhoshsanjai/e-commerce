import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.logging import request_id_var
from app.modules.audit.models import AuditLog


def record(
    db: Session,
    action: str,
    *,
    actor_id: uuid.UUID | None,
    request: Request | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """Add an audit entry to the caller's transaction. The caller commits."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500] if request else None,
            request_id=request_id_var.get(),
        )
    )

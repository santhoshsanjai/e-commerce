import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: uuid.UUID
    occurred_at: datetime
    action: str
    actor_name: str | None
    actor_email: str | None
    entity_type: str | None
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    ip: str | None
    request_id: str | None

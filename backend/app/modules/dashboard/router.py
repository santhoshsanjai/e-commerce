from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import DbSession, require_permission
from app.modules.dashboard import service
from app.modules.dashboard.schemas import Dashboard
from app.modules.users.models import User

router = APIRouter(prefix="/admin/dashboard", tags=["admin: dashboard"])


@router.get("")
def dashboard(
    db: DbSession, _: Annotated[User, Depends(require_permission("dashboard.view"))]
) -> Dashboard:
    return service.build(db)

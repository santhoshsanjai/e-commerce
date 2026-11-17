import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status

from app.core.dependencies import DbSession, require_permission
from app.core.exceptions import AppError
from app.infrastructure.storage import FileStore, get_file_store
from app.modules.courier_import import service
from app.modules.courier_import.schemas import CourierImportDetail, CourierImportOut
from app.modules.dispatch.excel import XLSX_CONTENT_TYPE
from app.modules.notifications.dependencies import SendQueuedEmails
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/admin/courier-imports", tags=["admin: courier import"])

CanImport = Annotated[User, Depends(require_permission("orders.import_courier"))]
Store = Annotated[FileStore, Depends(get_file_store)]
Paging = Annotated[PageParams, Depends(page_params)]

MAX_FILE_BYTES = 5 * 1024 * 1024


@router.post("", status_code=status.HTTP_201_CREATED)
def upload(
    request: Request,
    db: DbSession,
    store: Store,
    actor: CanImport,
    file: Annotated[UploadFile, File()],
) -> CourierImportDetail:
    """Upload a courier status file. Nothing changes until the preview is confirmed."""
    data = file.file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise AppError(
            "file_too_large",
            "Courier files must be 5 MB or smaller",
            status.HTTP_413_CONTENT_TOO_LARGE,
        )
    record = service.upload(db, store, actor, file.filename or "courier.xlsx", data, request)
    return service.detail(db, record)


@router.get("")
def list_imports(db: DbSession, _: CanImport, params: Paging) -> Page[CourierImportOut]:
    return service.list_imports(db, params)


@router.get("/{import_id}")
def get_import(import_id: uuid.UUID, db: DbSession, _: CanImport) -> CourierImportDetail:
    return service.detail(db, service.get(db, import_id))


@router.get("/{import_id}/error-report")
def error_report(
    import_id: uuid.UUID, request: Request, db: DbSession, actor: CanImport
) -> Response:
    """The rows that couldn't be applied, with the reason, as Excel. The courier can correct the
    rows in this file and send it back for upload."""
    data, name = service.error_report_file(db, import_id, actor, request)
    return Response(
        content=data,
        media_type=XLSX_CONTENT_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
            "Cache-Control": "no-store",
        },
    )


@router.post("/{import_id}/confirm", dependencies=[SendQueuedEmails])
def confirm(
    import_id: uuid.UUID, request: Request, db: DbSession, actor: CanImport
) -> CourierImportDetail:
    """Apply the previewed updates once. Rows are re-checked against current data first."""
    return service.detail(db, service.confirm(db, import_id, actor, request))

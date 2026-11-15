import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.dependencies import DbSession, require_permission
from app.infrastructure.storage import FileStore, get_file_store
from app.modules.dispatch import service
from app.modules.dispatch.excel import XLSX_CONTENT_TYPE
from app.modules.dispatch.schemas import CreateBatchIn, DispatchBatchDetail, DispatchBatchOut
from app.modules.orders.schemas import AdminOrderListItem
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/admin/dispatch-batches", tags=["admin: dispatch"])

CanExport = Annotated[User, Depends(require_permission("orders.export"))]
Store = Annotated[FileStore, Depends(get_file_store)]
Paging = Annotated[PageParams, Depends(page_params)]


@router.get("/eligible-orders")
def eligible_orders(db: DbSession, _: CanExport) -> list[AdminOrderListItem]:
    """Confirmed orders not yet handed to the courier (oldest first, up to 500)."""
    return service.eligible_orders(db)


@router.get("")
def list_batches(db: DbSession, _: CanExport, params: Paging) -> Page[DispatchBatchOut]:
    return service.list_batches(db, params)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_batch(
    data: CreateBatchIn, request: Request, db: DbSession, store: Store, actor: CanExport
) -> DispatchBatchDetail:
    batch = service.create_batch(db, store, actor, data.order_ids, request)
    return service.batch_detail(db, batch)


@router.get("/{batch_id}")
def get_batch(batch_id: uuid.UUID, db: DbSession, _: CanExport) -> DispatchBatchDetail:
    return service.batch_detail(db, service.get_batch(db, batch_id))


@router.get(
    "/{batch_id}/file",
    response_class=Response,
    responses={200: {"content": {XLSX_CONTENT_TYPE: {}}}},
)
def download_file(
    batch_id: uuid.UUID, request: Request, db: DbSession, store: Store, actor: CanExport
) -> Response:
    data, batch = service.download(db, store, batch_id, actor, request)
    return Response(
        content=data,
        media_type=XLSX_CONTENT_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{batch.file_name}"',
            "Cache-Control": "no-store",
        },
    )

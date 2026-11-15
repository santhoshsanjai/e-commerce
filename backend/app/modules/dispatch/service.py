import uuid
from datetime import UTC, datetime

from fastapi import Request, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.infrastructure.storage import FileStore
from app.modules.audit import service as audit
from app.modules.dispatch.excel import XLSX_CONTENT_TYPE, build_workbook
from app.modules.dispatch.models import DispatchBatch
from app.modules.dispatch.schemas import MAX_BATCH_ORDERS, DispatchBatchDetail, DispatchBatchOut
from app.modules.orders.lifecycle import EventSource, OrderStatus
from app.modules.orders.models import Order
from app.modules.orders.schemas import AdminOrderListItem
from app.modules.orders.service import apply_transition, to_admin_list_item
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams

ELIGIBLE = (OrderStatus.CONFIRMED, OrderStatus.READY_FOR_DISPATCH)


def eligible_orders(db: Session) -> list[AdminOrderListItem]:
    """Orders waiting to go to the courier, oldest first."""
    orders = db.scalars(
        select(Order)
        .where(Order.status.in_(ELIGIBLE), Order.dispatch_batch_id.is_(None))
        .order_by(Order.placed_at, Order.id)
        .limit(MAX_BATCH_ORDERS)
    ).all()
    return [to_admin_list_item(o) for o in orders]


def create_batch(
    db: Session,
    store: FileStore,
    actor: User,
    order_ids: list[uuid.UUID],
    request: Request | None = None,
) -> DispatchBatch:
    # Lock in a fixed order so two staff building overlapping batches can't deadlock; the second
    # one waits, then sees the orders are already batched.
    orders = list(
        db.scalars(
            select(Order).where(Order.id.in_(order_ids)).order_by(Order.id).with_for_update()
        ).all()
    )
    if len(orders) != len(order_ids):
        found = {o.id for o in orders}
        raise AppError(
            "order_not_found",
            "Some orders were not found",
            status.HTTP_404_NOT_FOUND,
            details={"missing": [str(i) for i in order_ids if i not in found]},
        )
    blocked = [o.order_number for o in orders if o.status not in ELIGIBLE or o.dispatch_batch_id]
    if blocked:
        raise AppError(
            "orders_not_eligible",
            "Some orders are already with the courier or can't be dispatched. Refresh the list.",
            status.HTTP_409_CONFLICT,
            details={"order_numbers": blocked},
        )

    now = datetime.now(UTC)
    seq = db.scalar(text("SELECT nextval('dispatch_batch_seq')"))
    batch_number = f"DSP-{now.year}-{seq:05d}"
    orders.sort(key=lambda o: (o.placed_at, o.order_number))
    batch = DispatchBatch(
        id=uuid.uuid4(),
        batch_number=batch_number,
        order_count=len(orders),
        cod_total_minor=sum(o.total_minor for o in orders if o.payment_method == "COD"),
        currency=orders[0].currency,
        file_key="",
        file_name=f"{batch_number}.xlsx",
        created_by_id=actor.id,
        created_at=now,
    )
    batch.file_key = f"dispatch/{now:%Y/%m}/{batch.id}/{batch.file_name}"
    db.add(batch)
    db.flush()

    for order in orders:
        order.dispatch_batch_id = batch.id
        apply_transition(
            order,
            OrderStatus.EXPORTED_TO_COURIER,
            source=EventSource.SYSTEM,
            actor_id=actor.id,
            reason=f"Added to dispatch batch {batch_number}",
            event_key=f"dispatch:{batch.id}:{order.id}",
            occurred_at=now,
        )

    # Upload before commit: if the upload fails nothing is saved and the orders stay eligible.
    store.put(batch.file_key, build_workbook(orders), XLSX_CONTENT_TYPE)
    audit.record(
        db,
        "dispatch.batch_created",
        actor_id=actor.id,
        request=request,
        entity_type="dispatch_batch",
        entity_id=str(batch.id),
        after={"batch_number": batch_number, "orders": [o.order_number for o in orders]},
    )
    db.commit()
    return batch


def _out(batch: DispatchBatch, creator: str | None) -> dict[str, object]:
    return {
        "id": batch.id,
        "batch_number": batch.batch_number,
        "order_count": batch.order_count,
        "cod_total_minor": batch.cod_total_minor,
        "currency": batch.currency,
        "file_name": batch.file_name,
        "created_by_name": creator,
        "created_at": batch.created_at,
    }


def list_batches(db: Session, params: PageParams) -> Page[DispatchBatchOut]:
    total = db.scalar(select(func.count()).select_from(DispatchBatch)) or 0
    rows = db.execute(
        select(DispatchBatch, User.full_name)
        .outerjoin(User, User.id == DispatchBatch.created_by_id)
        .order_by(DispatchBatch.created_at.desc(), DispatchBatch.id)
        .offset(params.offset)
        .limit(params.page_size)
    ).all()
    items = [DispatchBatchOut.model_validate(_out(b, name)) for b, name in rows]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


def get_batch(db: Session, batch_id: uuid.UUID) -> DispatchBatch:
    batch = db.get(DispatchBatch, batch_id)
    if batch is None:
        raise AppError("batch_not_found", "Dispatch batch not found", status.HTTP_404_NOT_FOUND)
    return batch


def batch_detail(db: Session, batch: DispatchBatch) -> DispatchBatchDetail:
    creator = db.get(User, batch.created_by_id) if batch.created_by_id else None
    orders = db.scalars(
        select(Order)
        .where(Order.dispatch_batch_id == batch.id)
        .order_by(Order.placed_at, Order.order_number)
    ).all()
    return DispatchBatchDetail.model_validate(
        {
            **_out(batch, creator.full_name if creator else None),
            "orders": [to_admin_list_item(o) for o in orders],
        }
    )


def download(
    db: Session, store: FileStore, batch_id: uuid.UUID, actor: User, request: Request | None
) -> tuple[bytes, DispatchBatch]:
    batch = get_batch(db, batch_id)
    data = store.get(batch.file_key)
    # The file holds customer names, phones and addresses, so every download is recorded.
    audit.record(
        db,
        "dispatch.file_downloaded",
        actor_id=actor.id,
        request=request,
        entity_type="dispatch_batch",
        entity_id=str(batch.id),
    )
    db.commit()
    return data, batch

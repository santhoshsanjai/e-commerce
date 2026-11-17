import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.infrastructure.storage import FileStore
from app.modules.audit import service as audit
from app.modules.courier_import import error_report
from app.modules.courier_import.models import CourierImport, ImportStatus
from app.modules.courier_import.parser import FileError, RawRow, parse
from app.modules.courier_import.schemas import CourierImportDetail, CourierImportOut
from app.modules.dispatch.excel import XLSX_CONTENT_TYPE
from app.modules.orders.lifecycle import (
    ORDER_STATUS_TEXT,
    EventSource,
    OrderStatus,
    can_transition,
    is_behind,
)
from app.modules.orders.models import Order
from app.modules.orders.service import apply_transition
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams

# Before handover the courier can't know the order; a row for one is a mistake in the file.
NOT_WITH_COURIER = frozenset(
    {OrderStatus.PENDING_CONFIRMATION, OrderStatus.CONFIRMED, OrderStatus.READY_FOR_DISPATCH}
)


class _State:
    """Order status and AWB as the rows are walked, so several rows for one order chain up."""

    def __init__(self, orders: dict[str, Order]) -> None:
        self.status = {n: o.status for n, o in orders.items()}
        self.awb = {n: o.awb_number for n, o in orders.items()}


def _plan(raw: RawRow, state: _State) -> dict[str, Any]:
    current = state.status.get(raw.order_number)
    out: dict[str, Any] = {
        "row": raw.row,
        "order_number": raw.order_number,
        "awb": raw.awb,
        "courier_status": raw.status_text,
        "current_status": current,
        "new_status": None,
        "outcome": "error",
        "message": raw.error or "",
    }
    if raw.error:
        return out
    if current is None:
        out["message"] = "Order not found"
        return out
    if current in NOT_WITH_COURIER:
        out["message"] = "This order hasn't been handed to the courier yet"
        return out

    changes: list[str] = []
    if raw.status and raw.status != current:
        if is_behind(current, raw.status):
            out["message"] = f"Already further along ({ORDER_STATUS_TEXT[current]})"
        elif can_transition(current, raw.status):
            out["new_status"] = raw.status
            changes.append(f"{ORDER_STATUS_TEXT[current]} → {ORDER_STATUS_TEXT[raw.status]}")
        else:
            out["message"] = (
                f"Can't move from {ORDER_STATUS_TEXT[current]} to {ORDER_STATUS_TEXT[raw.status]}"
            )
            return out
    if raw.awb and raw.awb != state.awb.get(raw.order_number):
        changes.append(f"AWB {raw.awb}")

    if changes:
        out["outcome"] = "will_update"
        out["message"] = "; ".join(changes)
        if out["new_status"]:
            state.status[raw.order_number] = out["new_status"]
        if raw.awb:
            state.awb[raw.order_number] = raw.awb
    else:
        out["outcome"] = "no_change"
        out["message"] = out["message"] or "Already up to date"
    return out


def _event_time(order: Order, reported: datetime | None, now: datetime) -> datetime:
    """Courier time, kept between the order's previous step and now so the history stays in
    order even when a courier clock or a typed date is off."""
    if reported is None:
        return now
    latest = max((e.occurred_at for e in order.events), default=order.placed_at)
    return min(max(reported, latest), now)


def _raw_json(raw: RawRow) -> dict[str, Any]:
    return {
        "row": raw.row,
        "order_number": raw.order_number,
        "awb": raw.awb,
        "status_text": raw.status_text,
        "status": raw.status,
        "occurred_at": raw.occurred_at.isoformat() if raw.occurred_at else None,
        "error": raw.error,
    }


def _raw_from_json(data: dict[str, Any]) -> RawRow:
    return RawRow(
        row=data["row"],
        order_number=data["order_number"],
        awb=data["awb"],
        status_text=data["status_text"],
        status=OrderStatus(data["status"]) if data["status"] else None,
        occurred_at=datetime.fromisoformat(data["occurred_at"]) if data["occurred_at"] else None,
        error=data["error"],
    )


def _summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(rows), "will_update": 0, "updated": 0, "no_change": 0, "error": 0}
    for r in rows:
        counts[r["plan"]["outcome"]] += 1
    return counts


def _orders_by_number(db: Session, numbers: set[str], lock: bool = False) -> dict[str, Order]:
    query = select(Order).where(Order.order_number.in_(numbers)).order_by(Order.id)
    if lock:
        query = query.with_for_update()
    return {o.order_number: o for o in db.scalars(query)}


def upload(
    db: Session,
    store: FileStore,
    actor: User,
    file_name: str,
    data: bytes,
    request: Request | None = None,
) -> CourierImport:
    try:
        raws = parse(data)
    except FileError as exc:
        raise AppError("invalid_file", str(exc), status.HTTP_422_UNPROCESSABLE_CONTENT) from exc
    orders = _orders_by_number(db, {r.order_number for r in raws if r.order_number})
    state = _State(orders)
    rows = [{"raw": _raw_json(r), "plan": _plan(r, state)} for r in raws]

    now = datetime.now(UTC)
    record = CourierImport(
        id=uuid.uuid4(),
        file_name=file_name[:200] or "courier.xlsx",
        file_key="",
        status=ImportStatus.PREVIEW,
        rows=rows,
        summary=_summary(rows),
        uploaded_by_id=actor.id,
        created_at=now,
    )
    record.file_key = f"courier-imports/{now:%Y/%m}/{record.id}.xlsx"
    store.put(record.file_key, data, XLSX_CONTENT_TYPE)
    db.add(record)
    audit.record(
        db,
        "courier_import.uploaded",
        actor_id=actor.id,
        request=request,
        entity_type="courier_import",
        entity_id=str(record.id),
        after={"file_name": record.file_name, "summary": record.summary},
    )
    db.commit()
    return record


def confirm(
    db: Session, import_id: uuid.UUID, actor: User, request: Request | None = None
) -> CourierImport:
    record = db.scalar(select(CourierImport).where(CourierImport.id == import_id).with_for_update())
    if record is None:
        raise AppError("import_not_found", "Courier import not found", status.HTTP_404_NOT_FOUND)
    if record.status is ImportStatus.CONFIRMED:
        return record  # Confirming twice applies nothing more.

    raws = [_raw_from_json(r["raw"]) for r in record.rows]
    # Re-check against current data: orders may have changed since the preview.
    orders = _orders_by_number(db, {r.order_number for r in raws if r.order_number}, lock=True)
    state = _State(orders)
    rows: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for raw in raws:
        plan = _plan(raw, state)
        if plan["outcome"] == "will_update":
            order = orders[raw.order_number]
            if raw.awb:
                order.awb_number = raw.awb
            if plan["new_status"]:
                apply_transition(
                    db,
                    order,
                    plan["new_status"],
                    source=EventSource.IMPORT,
                    actor_id=actor.id,
                    reason=f"Courier: {raw.status_text}",
                    event_key=f"courier:{record.id}:{raw.row}",
                    occurred_at=_event_time(order, raw.occurred_at, now),
                )
            plan["outcome"] = "updated"
        rows.append({"raw": _raw_json(raw), "plan": plan})

    record.rows = rows
    record.summary = _summary(rows)
    record.status = ImportStatus.CONFIRMED
    record.confirmed_by_id = actor.id
    record.confirmed_at = now
    audit.record(
        db,
        "courier_import.confirmed",
        actor_id=actor.id,
        request=request,
        entity_type="courier_import",
        entity_id=str(record.id),
        after={"summary": record.summary},
    )
    db.commit()
    return record


def _out(record: CourierImport, uploader: str | None) -> dict[str, Any]:
    return {
        "id": record.id,
        "file_name": record.file_name,
        "status": record.status,
        "summary": record.summary,
        "uploaded_by_name": uploader,
        "created_at": record.created_at,
        "confirmed_at": record.confirmed_at,
    }


def detail(db: Session, record: CourierImport) -> CourierImportDetail:
    uploader = db.get(User, record.uploaded_by_id) if record.uploaded_by_id else None
    return CourierImportDetail.model_validate(
        {
            **_out(record, uploader.full_name if uploader else None),
            "rows": [r["plan"] for r in record.rows],
        }
    )


def error_report_file(
    db: Session, import_id: uuid.UUID, actor: User, request: Request
) -> tuple[bytes, str]:
    """The rows that couldn't be applied, to send back to the courier. Audited like other
    courier file downloads."""
    record = get(db, import_id)
    rows = error_report.error_rows(record.rows)
    if not rows:
        raise AppError("no_error_rows", "Every row in this file was fine", status.HTTP_409_CONFLICT)
    audit.record(
        db,
        "courier_import.error_report_downloaded",
        actor_id=actor.id,
        request=request,
        entity_type="courier_import",
        entity_id=str(record.id),
        after={"rows": len(rows)},
    )
    db.commit()
    stem = record.file_name.rsplit(".", 1)[0][:80] or "courier"
    return error_report.build(rows), f"{stem} - rows to fix.xlsx"


def get(db: Session, import_id: uuid.UUID) -> CourierImport:
    record = db.get(CourierImport, import_id)
    if record is None:
        raise AppError("import_not_found", "Courier import not found", status.HTTP_404_NOT_FOUND)
    return record


def list_imports(db: Session, params: PageParams) -> Page[CourierImportOut]:
    total = db.scalar(select(func.count()).select_from(CourierImport)) or 0
    rows = db.execute(
        select(CourierImport, User.full_name)
        .outerjoin(User, User.id == CourierImport.uploaded_by_id)
        .order_by(CourierImport.created_at.desc(), CourierImport.id)
        .offset(params.offset)
        .limit(params.page_size)
    ).all()
    items = [CourierImportOut.model_validate(_out(r, name)) for r, name in rows]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)

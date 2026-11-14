"""Read a courier status file.

Header names and status words differ between couriers. Both are listed here so the real courier's
file can be supported by editing these two tables.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime

from openpyxl import load_workbook

from app.modules.dispatch.excel import IST
from app.modules.orders.lifecycle import OrderStatus

MAX_ROWS = 5000

HEADER_ALIASES: dict[str, set[str]] = {
    "order_number": {"order no", "order number", "order id", "reference no", "ref no", "order ref"},
    "awb": {
        "awb no",
        "awb",
        "awb number",
        "tracking no",
        "tracking number",
        "waybill",
        "waybill no",
    },
    "status": {"courier status", "status", "current status", "shipment status"},
    "occurred_at": {
        "status date",
        "status time",
        "date",
        "updated at",
        "last update",
        "event date",
    },
}

STATUS_WORDS: dict[str, OrderStatus] = {
    "dispatched": OrderStatus.DISPATCHED,
    "picked up": OrderStatus.DISPATCHED,
    "pickup done": OrderStatus.DISPATCHED,
    "shipped": OrderStatus.DISPATCHED,
    "in transit": OrderStatus.IN_TRANSIT,
    "intransit": OrderStatus.IN_TRANSIT,
    "reached hub": OrderStatus.IN_TRANSIT,
    "at hub": OrderStatus.IN_TRANSIT,
    "out for delivery": OrderStatus.OUT_FOR_DELIVERY,
    "ofd": OrderStatus.OUT_FOR_DELIVERY,
    "delivered": OrderStatus.DELIVERED,
    "undelivered": OrderStatus.DELIVERY_FAILED,
    "delivery failed": OrderStatus.DELIVERY_FAILED,
    "failed delivery": OrderStatus.DELIVERY_FAILED,
    "delivery attempted": OrderStatus.DELIVERY_FAILED,
    "ndr": OrderStatus.DELIVERY_FAILED,
    "rto": OrderStatus.RETURN_IN_TRANSIT,
    "rto initiated": OrderStatus.RETURN_IN_TRANSIT,
    "rto in transit": OrderStatus.RETURN_IN_TRANSIT,
    "return in transit": OrderStatus.RETURN_IN_TRANSIT,
    "rto delivered": OrderStatus.RETURNED,
    "returned": OrderStatus.RETURNED,
    "return delivered": OrderStatus.RETURNED,
}

_DATE_FORMATS = (
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


class FileError(ValueError):
    """The file can't be read as a courier status sheet. The message is shown to staff."""


@dataclass
class RawRow:
    row: int
    order_number: str
    awb: str
    status_text: str
    status: OrderStatus | None
    occurred_at: datetime | None
    error: str | None


def _norm(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"[\s_\-.:]+", " ", text).strip().lower()


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _date(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        moment = value
    else:
        for fmt in _DATE_FORMATS:
            try:
                moment = datetime.strptime(str(value).strip(), fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError
    # Courier times are Indian local time unless the cell carries a zone.
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=IST)
    return moment.astimezone(UTC)


def parse(data: bytes) -> list[RawRow]:
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise FileError("Upload the courier file as an Excel .xlsx workbook.")
    try:
        # openpyxl uses defusedxml (installed) to refuse XML bombs.
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises many types for broken files
        raise FileError(
            "This Excel file couldn't be read. Re-save it as .xlsx and try again."
        ) from exc
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = next(rows, None)
    if header is None:
        raise FileError("The sheet is empty.")
    columns: dict[str, int] = {}
    for index, heading in enumerate(header):
        name = _norm(heading)
        for field, aliases in HEADER_ALIASES.items():
            if name in aliases and field not in columns:
                columns[field] = index
    if "order_number" not in columns:
        raise FileError("No order number column found. Expected a header such as 'Order No'.")
    if "status" not in columns and "awb" not in columns:
        raise FileError("No status or AWB column found. Expected 'Courier Status' or 'AWB No'.")

    def cell(values: tuple[object, ...], field: str) -> object:
        index = columns.get(field)
        return values[index] if index is not None and index < len(values) else None

    parsed: list[RawRow] = []
    for number, values in enumerate(rows, start=2):
        if all(v in (None, "") for v in values):
            continue
        if len(parsed) >= MAX_ROWS:
            raise FileError(
                f"The file has more than {MAX_ROWS} rows. Split it and upload each part."
            )
        order_number = _text(cell(values, "order_number")).upper()
        awb = _text(cell(values, "awb"))[:64]
        status_text = _text(cell(values, "status"))
        error = None
        status = None
        if status_text:
            status = STATUS_WORDS.get(_norm(status_text))
            if status is None:
                error = f"Unknown courier status '{status_text[:40]}'"
        occurred_at = None
        try:
            occurred_at = _date(cell(values, "occurred_at"))
        except ValueError:
            error = error or "Status date not understood (use DD-MM-YYYY HH:MM)"
        if not order_number:
            error = "Order number is missing"
        elif not status_text and not awb:
            error = "No status or AWB number on this row"
        parsed.append(
            RawRow(number, order_number, awb, status_text[:80], status, occurred_at, error)
        )
    wb.close()
    if not parsed:
        raise FileError("The sheet has a header row but no data rows.")
    return parsed

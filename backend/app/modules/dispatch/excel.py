"""Courier dispatch sheet.

The column list below is the single place to change when the courier's own template arrives:
reorder, rename or drop entries and the export follows. Column headers are what the courier sees.
"""

import io
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta, timezone

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from app.modules.orders.models import Order

# ADR 0006: India only for v1. IST has no daylight saving, so a fixed offset is exact.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

Cell = str | int | float


@dataclass(frozen=True)
class Column:
    header: str
    width: int
    value: Callable[[Order], Cell]
    number_format: str | None = None


def _items(order: Order) -> str:
    text = "; ".join(f"{i.product_name} ({i.product_number}) x{i.qty}" for i in order.items)
    return text if len(text) <= 250 else text[:247] + "..."


def _cod_amount(order: Order) -> float:
    return order.total_minor / 100 if order.payment_method == "COD" else 0.0


COLUMNS: Sequence[Column] = (
    Column("Order No", 18, lambda o: o.order_number),
    Column("Order Date", 18, lambda o: o.placed_at.astimezone(IST).strftime("%d-%m-%Y %H:%M")),
    Column("Consignee Name", 24, lambda o: o.ship_name),
    Column("Mobile", 16, lambda o: o.ship_phone),
    Column("Address Line 1", 36, lambda o: o.ship_line1),
    Column("Address Line 2", 28, lambda o: o.ship_line2),
    Column("Landmark", 20, lambda o: o.ship_landmark),
    Column("City", 16, lambda o: o.ship_city),
    Column("State", 16, lambda o: o.ship_region),
    Column("PIN Code", 10, lambda o: o.ship_postal_code),
    Column("Country", 8, lambda o: o.ship_country_code),
    Column("Product Details", 40, _items),
    Column("Quantity", 9, lambda o: sum(i.qty for i in o.items)),
    Column("Payment Mode", 13, lambda o: str(o.payment_method)),
    Column("COD Amount", 12, _cod_amount, "0.00"),
    Column("Declared Value", 14, lambda o: o.total_minor / 100, "0.00"),
    Column("Delivery Instructions", 30, lambda o: o.delivery_instructions),
    # Left blank for the courier to fill in; the import reads them back.
    Column("AWB No", 18, lambda o: ""),
    Column("Courier Status", 16, lambda o: ""),
)

_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
_PHONE_OR_NUMBER = re.compile(r"^[+-]?[0-9][0-9 .\-]*$")


def safe_text(value: Cell) -> Cell:
    """Stop customer-entered text being run as a formula if the sheet is re-saved as CSV and
    reopened (CSV injection). Phone numbers such as +91 98765 43210 are left as they are."""
    if (
        isinstance(value, str)
        and value.startswith(_FORMULA_START)
        and not _PHONE_OR_NUMBER.match(value)
    ):
        return "'" + value
    return value


def build_workbook(orders: Sequence[Order]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Orders"
    ws.append([c.header for c in COLUMNS])
    header_fill = PatternFill("solid", fgColor="1F4E79")
    for idx, column in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        ws.column_dimensions[get_column_letter(idx)].width = column.width

    for order in orders:
        ws.append([safe_text(c.value(order)) for c in COLUMNS])
        row = ws.max_row
        for idx, column in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=row, column=idx)
            if column.number_format:
                cell.number_format = column.number_format
            elif isinstance(cell.value, str):
                # Keep PIN codes and phone numbers as text so Excel doesn't drop leading digits.
                cell.number_format = "@"

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

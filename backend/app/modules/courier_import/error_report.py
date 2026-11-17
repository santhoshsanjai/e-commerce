"""The rows of a courier file that couldn't be applied, as an Excel file to send back.

The first four columns use the import's own headings, so once the courier has corrected the rows
the same file can be uploaded again; the extra "Problem" and "Row in your file" columns are
ignored by the import.
"""

import io
from datetime import datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.modules.dispatch.excel import safe_text
from app.shared.timezones import IST

HEADERS = ("Order No", "AWB No", "Courier Status", "Status Date", "Problem", "Row in your file")
WIDTHS = (20, 20, 20, 18, 60, 16)


def error_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r["plan"]["outcome"] == "error"]


def _when(value: str | None) -> str:
    if not value:
        return ""
    return datetime.fromisoformat(value).astimezone(IST).strftime("%d-%m-%Y %H:%M")


def build(rows: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Rows to fix"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="FDECEA")
    for r in rows:
        raw = r["raw"]
        ws.append(
            [
                safe_text(raw["order_number"]),
                safe_text(raw["awb"]),
                safe_text(raw["status_text"]),
                _when(raw["occurred_at"]),
                safe_text(r["plan"]["message"]),
                raw["row"],
            ]
        )
    for index, width in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width
    for row in ws.iter_rows(min_row=2, min_col=5, max_col=5):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

"""Sales report workbook: the on-screen report plus every order in the range, for accounts."""

import io
from collections.abc import Sequence
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.modules.dispatch.excel import safe_text
from app.modules.orders.lifecycle import ORDER_STATUS_TEXT
from app.modules.orders.models import Order
from app.modules.reports.schemas import ProductRow, SalesReport
from app.shared.timezones import IST

MONEY = "#,##0.00"
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF")

Value = str | int | float | datetime | None


def _rupees(minor: int) -> float:
    return minor / 100


def _table(
    ws: Worksheet,
    headers: Sequence[tuple[str, int, str | None]],
    rows: Sequence[Sequence[Value]],
    first_row: int = 1,
) -> None:
    for col, (title, width, _) in enumerate(headers, start=1):
        cell = ws.cell(row=first_row, column=col, value=title)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        ws.column_dimensions[get_column_letter(col)].width = width
    for r, row in enumerate(rows, start=first_row + 1):
        for col, value in enumerate(row, start=1):
            cell = ws.cell(
                row=r, column=col, value=safe_text(value) if isinstance(value, str) else value
            )
            fmt = headers[col - 1][2]
            if fmt:
                cell.number_format = fmt
    ws.freeze_panes = f"A{first_row + 1}"


def build_workbook(
    report: SalesReport, all_products: Sequence[ProductRow], orders: Sequence[Order]
) -> bytes:
    wb = Workbook()
    s = report.summary

    ws = wb.active
    assert ws is not None
    ws.title = "Summary"
    ws["A1"] = "Sales report"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (
        f"{report.date_from:%d %b %Y} to {report.date_to:%d %b %Y} (India time). "
        f"Amounts in {report.currency}."
    )
    ws["A3"] = "Sales exclude cancelled and returned orders, which are listed separately below."
    summary_rows: list[Sequence[Value]] = [
        ("Orders", s.orders, None),
        ("Sales", _rupees(s.sales_minor), MONEY),
        ("Average order value", _rupees(s.avg_order_minor), MONEY),
        ("Items sold", s.items_sold, None),
        ("Delivered orders", s.delivered_orders, None),
        ("Delivered value", _rupees(s.delivered_minor), MONEY),
        ("Cash on delivery collected", _rupees(s.cod_collected_minor), MONEY),
        ("Cancelled orders", s.cancelled_orders, None),
        ("Cancelled value", _rupees(s.cancelled_minor), MONEY),
        ("Returned orders", s.returned_orders, None),
        ("Returned value", _rupees(s.returned_minor), MONEY),
    ]
    for i, (label, value, fmt) in enumerate(summary_rows, start=5):
        ws.cell(row=i, column=1, value=label).font = Font(bold=True)
        cell = ws.cell(row=i, column=2, value=value)
        if fmt:
            cell.number_format = str(fmt)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 18

    period_title = {"day": "Day", "week": "Week starting", "month": "Month"}[report.group_by]
    _table(
        wb.create_sheet("By period"),
        [
            (period_title, 18, None),
            ("Orders", 10, None),
            ("Items sold", 12, None),
            ("Sales", 16, MONEY),
        ],
        [(p.label, p.orders, p.items_sold, _rupees(p.sales_minor)) for p in report.periods],
    )
    _table(
        wb.create_sheet("Products"),
        [
            ("Product No", 14, None),
            ("Product", 40, None),
            ("Qty sold", 10, None),
            ("Sales", 16, MONEY),
        ],
        [(p.product_number, p.product_name, p.qty, _rupees(p.sales_minor)) for p in all_products],
    )
    _table(
        wb.create_sheet("By state"),
        [("State", 24, None), ("Orders", 10, None), ("Sales", 16, MONEY)],
        [(g.region, g.orders, _rupees(g.sales_minor)) for g in report.regions],
    )
    _table(
        wb.create_sheet("Orders"),
        [
            ("Order No", 18, None),
            ("Placed", 18, "dd-mm-yyyy hh:mm"),
            ("Status", 20, None),
            ("Payment", 10, None),
            ("Payment status", 14, None),
            ("Customer", 24, None),
            ("City", 16, None),
            ("State", 16, None),
            ("Items", 8, None),
            ("Subtotal", 14, MONEY),
            ("Shipping", 12, MONEY),
            ("Discount", 12, MONEY),
            ("Tax", 12, MONEY),
            ("Total", 14, MONEY),
        ],
        [
            (
                o.order_number,
                o.placed_at.astimezone(IST).replace(tzinfo=None),
                ORDER_STATUS_TEXT[o.status],
                o.payment_method.value,
                o.payment_status.value.title(),
                o.customer_name,
                o.ship_city,
                o.ship_region,
                sum(i.qty for i in o.items),
                _rupees(o.subtotal_minor),
                _rupees(o.shipping_minor),
                _rupees(o.discount_minor),
                _rupees(o.tax_minor),
                _rupees(o.total_minor),
            )
            for o in orders
        ],
    )
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

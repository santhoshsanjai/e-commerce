from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.dependencies import DbSession, require_permission
from app.modules.audit import service as audit
from app.modules.dispatch.excel import XLSX_CONTENT_TYPE
from app.modules.reports import excel, service
from app.modules.reports.schemas import GroupBy, SalesReport
from app.modules.users.models import User

router = APIRouter(prefix="/admin/reports", tags=["admin: reports"])

CanViewReports = Annotated[User, Depends(require_permission("reports.view"))]


@router.get("/sales")
def sales_report(
    db: DbSession,
    _: CanViewReports,
    date_from: date | None = None,
    date_to: date | None = None,
    group_by: Annotated[GroupBy, Query()] = GroupBy.DAY,
) -> SalesReport:
    return service.build(db, service.resolve_range(date_from, date_to), group_by)


@router.get("/sales/export", response_class=Response)
def export_sales_report(
    request: Request,
    db: DbSession,
    actor: CanViewReports,
    date_from: date | None = None,
    date_to: date | None = None,
    group_by: Annotated[GroupBy, Query()] = GroupBy.DAY,
) -> Response:
    r = service.resolve_range(date_from, date_to)
    report = service.build(db, r, group_by)
    content = excel.build_workbook(report, service.products(db, r), service.orders_in_range(db, r))
    # Exports contain customer names, so who downloaded what is recorded.
    audit.record(
        db,
        "reports.sales_exported",
        actor_id=actor.id,
        request=request,
        entity_type="report",
        entity_id="sales",
        after={"date_from": r.date_from.isoformat(), "date_to": r.date_to.isoformat()},
    )
    db.commit()
    name = f"sales-{r.date_from:%Y%m%d}-{r.date_to:%Y%m%d}.xlsx"
    return Response(
        content,
        media_type=XLSX_CONTENT_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.catalog.models import Product, ProductSku, ProductStatus
from app.modules.courier_import.models import CourierImport, ImportStatus
from app.modules.dashboard.schemas import Attention, Dashboard, DaySales, LowStockItem
from app.modules.orders.lifecycle import OrderStatus
from app.modules.orders.models import Order
from app.modules.returns import service as returns_service
from app.shared.timezones import IST

S = OrderStatus
# Orders that never turned into a sale are left out of sales figures.
NOT_SALES = (S.CANCELLED, S.RETURNED, S.RETURN_IN_TRANSIT)
WITH_COURIER = (
    S.EXPORTED_TO_COURIER,
    S.DISPATCHED,
    S.IN_TRANSIT,
    S.OUT_FOR_DELIVERY,
    S.DELIVERY_FAILED,
)


def build(db: Session, today: date | None = None) -> Dashboard:
    """Operational summary. Days are Indian calendar days (ADR 0006)."""
    today = today or datetime.now(IST).date()
    start = datetime.combine(today - timedelta(days=6), time.min, IST).astimezone(UTC)
    local_day = cast(func.timezone("Asia/Kolkata", Order.placed_at), Date)

    rows = db.execute(
        select(local_day, func.count(), func.coalesce(func.sum(Order.total_minor), 0))
        .where(Order.placed_at >= start, Order.status.not_in(NOT_SALES))
        .group_by(local_day)
    ).all()
    by_day = {d: (n, int(total)) for d, n, total in rows}
    week = [
        DaySales(day=d, orders=by_day.get(d, (0, 0))[0], sales_minor=by_day.get(d, (0, 0))[1])
        for d in (today - timedelta(days=i) for i in range(6, -1, -1))
    ]

    counts = dict(db.execute(select(Order.status, func.count()).group_by(Order.status)).all())
    cod = db.scalar(
        select(func.coalesce(func.sum(Order.total_minor), 0)).where(
            Order.status.in_(WITH_COURIER), Order.payment_method == "COD"
        )
    )
    awaiting = db.scalar(
        select(func.count()).where(
            Order.status.in_((S.CONFIRMED, S.READY_FOR_DISPATCH)),
            Order.dispatch_batch_id.is_(None),
        )
    )
    low = db.execute(
        select(Product.id, Product.product_number, Product.name, ProductSku.stock_qty)
        .join(ProductSku, ProductSku.product_id == Product.id)
        .where(
            Product.status == ProductStatus.PUBLISHED,
            ProductSku.stock_qty <= ProductSku.low_stock_threshold,
        )
        .order_by(ProductSku.stock_qty, Product.name)
        .limit(10)
    ).all()
    pending_imports = db.scalar(
        select(func.count()).where(CourierImport.status == ImportStatus.PREVIEW)
    )

    return Dashboard(
        currency=get_settings().default_currency,
        today=week[-1],
        last_7_days=week,
        cod_with_courier_minor=int(cod or 0),
        status_counts={s: counts.get(s, 0) for s in OrderStatus},
        attention=Attention(
            awaiting_dispatch=awaiting or 0,
            delivery_failed=counts.get(S.DELIVERY_FAILED, 0),
            on_hold=counts.get(S.ON_HOLD, 0),
            returning=counts.get(S.RETURN_IN_TRANSIT, 0),
            imports_not_applied=pending_imports or 0,
            returns_open=returns_service.open_count(db),
            low_stock=[
                LowStockItem(product_id=i, product_number=n, name=nm, stock_qty=q)
                for i, n, nm, q in low
            ],
        ),
    )

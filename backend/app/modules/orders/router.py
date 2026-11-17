import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import CurrentBuyer, DbSession, require_permission
from app.modules.access_control.service import permissions_for
from app.modules.notifications.dependencies import SendQueuedEmails
from app.modules.orders import service
from app.modules.orders.lifecycle import OrderStatus
from app.modules.orders.schemas import (
    AdminOrderDetail,
    AdminOrderListItem,
    BuyerCancelIn,
    OrderDetail,
    OrderSummary,
    StatusChangeIn,
)
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams, page_params

buyer_router = APIRouter(prefix="/me/orders", tags=["buyer: orders"])
admin_router = APIRouter(prefix="/admin/orders", tags=["admin: orders"])

Paging = Annotated[PageParams, Depends(page_params)]
CanViewOrders = Annotated[User, Depends(require_permission("orders.view"))]
CanUpdateStatus = Annotated[User, Depends(require_permission("orders.status.update"))]


@buyer_router.get("")
def my_orders(db: DbSession, user: CurrentBuyer, params: Paging) -> Page[OrderSummary]:
    return service.list_my_orders(db, user, params)


@buyer_router.get("/{order_number}")
def my_order(order_number: str, db: DbSession, user: CurrentBuyer) -> OrderDetail:
    return service.to_detail(service.get_my_order(db, user, order_number))


@buyer_router.post("/{order_number}/cancel", dependencies=[SendQueuedEmails])
def cancel_my_order(
    order_number: str, data: BuyerCancelIn, request: Request, db: DbSession, user: CurrentBuyer
) -> OrderDetail:
    """Cancel before the order is handed to the courier. The stock goes back on sale."""
    return service.to_detail(service.cancel_by_buyer(db, user, order_number, data.reason, request))


@admin_router.get("")
def admin_orders(
    db: DbSession,
    _: CanViewOrders,
    params: Paging,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[AdminOrderListItem]:
    return service.list_admin_orders(db, params, q, status_filter, date_from, date_to)


@admin_router.get("/{order_id}")
def admin_order(order_id: uuid.UUID, db: DbSession, _: CanViewOrders) -> AdminOrderDetail:
    return service.to_admin_detail(service.get_order(db, order_id))


@admin_router.post("/{order_id}/status", dependencies=[SendQueuedEmails])
def change_status(
    order_id: uuid.UUID,
    data: StatusChangeIn,
    request: Request,
    db: DbSession,
    actor: CanUpdateStatus,
) -> AdminOrderDetail:
    """Move an order to another status. Steps outside the lifecycle need `override: true`, the
    `orders.status.override` permission and a reason. Cancelling before handover restocks."""
    can_override = "orders.status.override" in permissions_for(actor)
    order = service.change_status(db, order_id, data, actor, can_override, request)
    return service.to_admin_detail(order)

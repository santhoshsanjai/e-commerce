import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import CurrentBuyer, DbSession, require_permission
from app.modules.notifications.dependencies import SendQueuedEmails
from app.modules.returns import service
from app.modules.returns.models import ReturnStatus
from app.modules.returns.schemas import (
    AdminReturnOut,
    DecisionIn,
    ReceiveIn,
    RefundIn,
    ReturnEligibility,
    ReturnOut,
    ReturnRequestIn,
)
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams, page_params

buyer_router = APIRouter(tags=["buyer: returns"])
admin_router = APIRouter(prefix="/admin/returns", tags=["admin: returns"])

Paging = Annotated[PageParams, Depends(page_params)]
CanView = Annotated[User, Depends(require_permission("returns.view"))]
CanManage = Annotated[User, Depends(require_permission("returns.manage"))]


@buyer_router.get("/me/orders/{order_number}/return")
def my_return(order_number: str, db: DbSession, user: CurrentBuyer) -> ReturnEligibility:
    """Whether this order can be returned (and until when), and its return if there is one."""
    return service.eligibility(db, user, order_number)


@buyer_router.post(
    "/me/orders/{order_number}/return", status_code=201, dependencies=[SendQueuedEmails]
)
def request_return(
    order_number: str, data: ReturnRequestIn, request: Request, db: DbSession, user: CurrentBuyer
) -> ReturnOut:
    """Ask to return some or all items of a delivered order, within the return window."""
    return service.to_out(service.request_return(db, user, order_number, data, request))


@buyer_router.post("/me/returns/{return_number}/withdraw")
def withdraw_return(
    return_number: str, request: Request, db: DbSession, user: CurrentBuyer
) -> ReturnOut:
    """Take back a return request before the shop has decided on it."""
    return service.to_out(service.withdraw(db, user, return_number, request))


@admin_router.get("")
def list_returns(
    db: DbSession,
    _: CanView,
    params: Paging,
    status_filter: Annotated[ReturnStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[AdminReturnOut]:
    return service.list_returns(db, params, status_filter, q)


@admin_router.get("/{return_id}")
def get_return(return_id: uuid.UUID, db: DbSession, _: CanView) -> AdminReturnOut:
    return service.to_admin_out(service.get(db, return_id))


@admin_router.post("/{return_id}/approve", dependencies=[SendQueuedEmails])
def approve(
    return_id: uuid.UUID, data: DecisionIn, request: Request, db: DbSession, actor: CanManage
) -> AdminReturnOut:
    """Accept the return. The note goes to the buyer (e.g. how the pickup works)."""
    return service.to_admin_out(service.approve(db, return_id, data.note, actor, request))


@admin_router.post("/{return_id}/reject", dependencies=[SendQueuedEmails])
def reject(
    return_id: uuid.UUID, data: DecisionIn, request: Request, db: DbSession, actor: CanManage
) -> AdminReturnOut:
    """Refuse the return; the note (required) tells the buyer why."""
    return service.to_admin_out(service.reject(db, return_id, data.note, actor, request))


@admin_router.post("/{return_id}/receive")
def receive(
    return_id: uuid.UUID, data: ReceiveIn, request: Request, db: DbSession, actor: CanManage
) -> AdminReturnOut:
    """The items are back. Those listed in `restock` go back on sale."""
    return service.to_admin_out(service.receive(db, return_id, data.restock, actor, request))


@admin_router.post("/{return_id}/refund", dependencies=[SendQueuedEmails])
def refund(
    return_id: uuid.UUID, data: RefundIn, request: Request, db: DbSession, actor: CanManage
) -> AdminReturnOut:
    """Record a refund paid outside the shop (UPI, bank transfer, cash) and tell the buyer."""
    return service.to_admin_out(service.refund(db, return_id, data, actor, request))

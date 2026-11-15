from typing import Annotated

from fastapi import APIRouter, Header, Response, status

from app.core.dependencies import CurrentBuyer, DbSession
from app.modules.checkout import service
from app.modules.checkout.schemas import CheckoutRequest
from app.modules.orders.schemas import OrderDetail
from app.modules.orders.service import to_detail

router = APIRouter(tags=["buyer: checkout"])


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
def checkout(
    data: CheckoutRequest,
    response: Response,
    db: DbSession,
    user: CurrentBuyer,
    idempotency_key: Annotated[
        str,
        Header(
            min_length=8,
            max_length=100,
            description="Unique per checkout attempt; a retry with the same key returns that order",
        ),
    ],
) -> OrderDetail:
    order, created = service.place_order(db, user, data, idempotency_key)
    if not created:
        response.status_code = status.HTTP_200_OK
    return to_detail(order)

"""Order lifecycle: statuses and allowed transitions (handoff section 6).

One map is shared by checkout, manual status updates and courier imports so every path follows the
same rules. Transitions outside it need the `orders.status.override` permission and a reason.
"""

import enum


class OrderStatus(enum.StrEnum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH"
    EXPORTED_TO_COURIER = "EXPORTED_TO_COURIER"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    # Exception states
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    RETURN_IN_TRANSIT = "RETURN_IN_TRANSIT"
    RETURNED = "RETURNED"


class PaymentMethod(enum.StrEnum):
    COD = "COD"


class PaymentStatus(enum.StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class EventSource(enum.StrEnum):
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    BUYER = "BUYER"


S = OrderStatus

TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    S.PENDING_CONFIRMATION: frozenset({S.CONFIRMED, S.CANCELLED, S.ON_HOLD}),
    S.CONFIRMED: frozenset({S.READY_FOR_DISPATCH, S.EXPORTED_TO_COURIER, S.CANCELLED, S.ON_HOLD}),
    S.READY_FOR_DISPATCH: frozenset({S.EXPORTED_TO_COURIER, S.CANCELLED, S.ON_HOLD}),
    S.EXPORTED_TO_COURIER: frozenset(
        {S.DISPATCHED, S.IN_TRANSIT, S.OUT_FOR_DELIVERY, S.DELIVERED, S.CANCELLED, S.ON_HOLD}
    ),
    S.DISPATCHED: frozenset(
        {S.IN_TRANSIT, S.OUT_FOR_DELIVERY, S.DELIVERED, S.DELIVERY_FAILED, S.RETURN_IN_TRANSIT}
    ),
    S.IN_TRANSIT: frozenset(
        {S.OUT_FOR_DELIVERY, S.DELIVERED, S.DELIVERY_FAILED, S.RETURN_IN_TRANSIT}
    ),
    S.OUT_FOR_DELIVERY: frozenset(
        {S.DELIVERED, S.DELIVERY_FAILED, S.IN_TRANSIT, S.RETURN_IN_TRANSIT}
    ),
    S.DELIVERY_FAILED: frozenset({S.OUT_FOR_DELIVERY, S.IN_TRANSIT, S.RETURN_IN_TRANSIT}),
    S.DELIVERED: frozenset({S.COMPLETED}),
    S.RETURN_IN_TRANSIT: frozenset({S.RETURNED}),
    S.ON_HOLD: frozenset({S.CONFIRMED, S.READY_FOR_DISPATCH, S.CANCELLED}),
    S.COMPLETED: frozenset(),
    S.CANCELLED: frozenset(),
    S.RETURNED: frozenset(),
}

# Before handover to the courier, cancelling puts stock back on the shelf.
CANCELLABLE_WITH_RESTOCK = frozenset(
    {S.PENDING_CONFIRMATION, S.CONFIRMED, S.READY_FOR_DISPATCH, S.ON_HOLD}
)


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in TRANSITIONS[current]

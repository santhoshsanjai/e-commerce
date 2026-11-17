import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base, TimestampMixin
from app.modules.orders.models import Order, OrderItem


class ReturnStatus(enum.StrEnum):
    REQUESTED = "REQUESTED"  # the buyer asked; staff haven't decided
    APPROVED = "APPROVED"  # staff agreed; the parcel is on its way back
    REJECTED = "REJECTED"
    RECEIVED = "RECEIVED"  # the items are back with us
    REFUNDED = "REFUNDED"
    WITHDRAWN = "WITHDRAWN"  # the buyer changed their mind before a decision


# A return in one of these states blocks a second return on the same order.
OPEN_STATUSES = frozenset(
    {ReturnStatus.REQUESTED, ReturnStatus.APPROVED, ReturnStatus.RECEIVED, ReturnStatus.REFUNDED}
)


class ReturnReason(enum.StrEnum):
    DAMAGED = "DAMAGED"
    WRONG_ITEM = "WRONG_ITEM"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    NO_LONGER_NEEDED = "NO_LONGER_NEEDED"
    OTHER = "OTHER"


class RefundMethod(enum.StrEnum):
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    CASH = "CASH"
    OTHER = "OTHER"


def _enum(cls: type, name: str) -> Enum:
    return Enum(cls, name=name, native_enum=False, length=32)


class ReturnRequest(TimestampMixin, Base):
    """A buyer's request to send items back, and what happened to it (ADR 0010)."""

    __tablename__ = "return_requests"
    __table_args__ = (
        # One return per order at a time; a rejected or withdrawn one doesn't count.
        Index(
            "uq_return_requests_one_open_per_order",
            "order_id",
            unique=True,
            postgresql_where=text("status IN ('REQUESTED', 'APPROVED', 'RECEIVED', 'REFUNDED')"),
        ),
        CheckConstraint("refund_minor IS NULL OR refund_minor > 0", name="refund_positive"),
        Index("ix_return_requests_status_requested_at", "status", "requested_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    return_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[ReturnStatus] = mapped_column(
        _enum(ReturnStatus, "return_status"), nullable=False
    )
    reason: Mapped[ReturnReason] = mapped_column(
        _enum(ReturnReason, "return_reason"), nullable=False
    )
    buyer_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Shown to the buyer with the decision (e.g. why it was rejected, how to send it back).
    decision_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    refund_minor: Mapped[int | None] = mapped_column(BigInteger)
    refund_method: Mapped[RefundMethod | None] = mapped_column(_enum(RefundMethod, "refund_method"))
    refund_reference: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    order: Mapped[Order] = relationship(lazy="joined", innerjoin=True)
    items: Mapped[list["ReturnItem"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="ReturnItem.position"
    )


class ReturnItem(Base):
    __tablename__ = "return_items"
    __table_args__ = (CheckConstraint("qty > 0", name="qty_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    return_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("return_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    # Put back on sale when the parcel came back (staff choose, e.g. not if damaged).
    restocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    order_item: Mapped[OrderItem] = relationship(lazy="joined")

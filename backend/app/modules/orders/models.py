import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base, TimestampMixin
from app.modules.orders.lifecycle import EventSource, OrderStatus, PaymentMethod, PaymentStatus


def _enum(cls: type, name: str) -> Enum:
    return Enum(cls, name=name, native_enum=False, length=32)


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        CheckConstraint(
            "total_minor = subtotal_minor + shipping_minor + tax_minor - discount_minor",
            name="total_adds_up",
        ),
        CheckConstraint("total_minor >= 0", name="total_non_negative"),
        Index("ix_orders_status_placed_at", "status", "placed_at"),
        Index("ix_orders_ship_phone", "ship_phone"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus, "order_status"), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        _enum(PaymentMethod, "payment_method"), nullable=False
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        _enum(PaymentStatus, "payment_status"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shipping_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Customer and delivery details copied at order time.
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    ship_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ship_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    ship_line1: Mapped[str] = mapped_column(String(200), nullable=False)
    ship_line2: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    ship_landmark: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    ship_city: Mapped[str] = mapped_column(String(100), nullable=False)
    ship_region: Mapped[str] = mapped_column(String(100), nullable=False)
    ship_postal_code: Mapped[str] = mapped_column(String(12), nullable=False)
    ship_country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    delivery_instructions: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    # Courier tracking number, filled from the courier's status file.
    awb_number: Mapped[str | None] = mapped_column(String(64), index=True)
    # Set when the order is put in a courier dispatch batch; an order joins at most one batch.
    dispatch_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("dispatch_batches.id", ondelete="RESTRICT"), index=True
    )
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    items: Mapped[list["OrderItem"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="OrderItem.position"
    )
    events: Mapped[list["OrderStatusEvent"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="OrderStatusEvent.occurred_at"
    )


class OrderItem(Base):
    """Snapshot of what was bought. Never updated after the order is placed."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="qty_positive"),
        CheckConstraint(
            "line_total_minor = unit_price_minor * qty + tax_minor - discount_minor",
            name="line_total_adds_up",
        ),
        Index("ix_order_items_product_number", "product_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    sku_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("product_skus.id", ondelete="SET NULL")
    )
    product_number: Mapped[str] = mapped_column(String(20), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    line_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)


class OrderStatusEvent(Base):
    """Append-only status history. Rows are never updated or deleted."""

    __tablename__ = "order_status_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(_enum(OrderStatus, "order_status"))
    to_status: Mapped[OrderStatus] = mapped_column(
        _enum(OrderStatus, "order_status"), nullable=False
    )
    source: Mapped[EventSource] = mapped_column(_enum(EventSource, "event_source"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    # Stable key for idempotent imports (e.g. order + status + courier event time).
    event_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base, TimestampMixin
from app.modules.catalog.models import ProductSku

MAX_LINE_QTY = 20


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    items: Mapped[list["CartItem"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="CartItem.created_at"
    )


class CartItem(TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "sku_id"),
        CheckConstraint(f"qty BETWEEN 1 AND {MAX_LINE_QTY}", name="qty_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cart_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_skus.id", ondelete="CASCADE"), nullable=False
    )
    qty: Mapped[int] = mapped_column(Integer, nullable=False)

    sku: Mapped[ProductSku] = relationship(lazy="joined")

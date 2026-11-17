import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base, TimestampMixin


class ShopCharges(TimestampMixin, Base):
    """Delivery charge and GST rules: one row (id = 1), edited in the admin portal (ADR 0009)."""

    __tablename__ = "shop_charges"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("shipping_fee_minor >= 0", name="shipping_non_negative"),
        CheckConstraint(
            "free_shipping_over_minor IS NULL OR free_shipping_over_minor > 0",
            name="free_shipping_positive",
        ),
        CheckConstraint("default_gst_rate_bp BETWEEN 0 AND 4000", name="gst_rate_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    shipping_fee_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    # Orders whose items add up to at least this much ship free. None: never free.
    free_shipping_over_minor: Mapped[int | None] = mapped_column(BigInteger)
    # True: product prices already include GST (shown as "includes GST"). False: GST is added.
    prices_include_gst: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Basis points: 1800 = 18%. Used for products without their own rate.
    default_gst_rate_bp: Mapped[int] = mapped_column(Integer, nullable=False, default=1800)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

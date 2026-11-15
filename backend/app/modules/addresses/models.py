import uuid

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base, TimestampMixin


class Address(TimestampMixin, Base):
    """A buyer's saved delivery address. Orders copy it, so later edits never change an order."""

    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recipient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    line1: Mapped[str] = mapped_column(String(200), nullable=False)
    line2: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    landmark: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(12), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="IN")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

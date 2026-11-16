import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base, TimestampMixin


class StorefrontSettings(TimestampMixin, Base):
    """The shop's look: one row (id = 1). Colours are overrides of the design tokens in
    frontend/projects/shared/styles/_tokens.scss; a token left out uses that default."""

    __tablename__ = "storefront_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    store_name: Mapped[str] = mapped_column(String(60), nullable=False, default="Shop")
    announcement: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    colors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

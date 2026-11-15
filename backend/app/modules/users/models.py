import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.access_control.models import Role


class UserType(enum.StrEnum):
    BUYER = "BUYER"
    STAFF = "STAFF"


# JWT audience per account type, so a buyer token can never call staff routes.
AUDIENCE_FOR: dict[UserType, str] = {UserType.BUYER: "buyer", UserType.STAFF: "staff"}


class User(TimestampMixin, Base):
    """Buyers and staff share one table; `user_type` decides which login route they may use."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Stored lower-cased; uniqueness is enforced on the normalised value.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType, name="user_type", native_enum=False, length=16), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles", lazy="selectin", back_populates="users"
    )

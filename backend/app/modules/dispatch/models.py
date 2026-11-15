import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class DispatchBatch(Base):
    """A set of orders handed to the courier together, with the Excel file that was sent.

    The file is kept as generated so a re-download always matches what the courier received.
    """

    __tablename__ = "dispatch_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cod_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    file_key: Mapped[str] = mapped_column(String(300), nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

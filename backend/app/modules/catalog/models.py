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


class ProductStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class MediaType(enum.StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        Index(
            "ix_products_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_products_status_published_at", "status", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Human-readable, unique, never reused (from a database sequence) and immutable after creation.
    product_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("brands.id", ondelete="RESTRICT")
    )
    short_description: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status", native_enum=False, length=16),
        nullable=False,
        default=ProductStatus.DRAFT,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    category: Mapped[Category] = relationship(lazy="joined")
    brand: Mapped[Brand | None] = relationship(lazy="joined")
    skus: Mapped[list["ProductSku"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="ProductSku.created_at"
    )
    attributes: Mapped[list["ProductAttribute"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="ProductAttribute.sort_order"
    )
    media: Mapped[list["ProductMedia"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="ProductMedia.sort_order"
    )

    @property
    def default_sku(self) -> "ProductSku":
        return next(s for s in self.skus if s.is_default)

    @property
    def primary_image(self) -> "ProductMedia | None":
        return next((m for m in self.media if m.is_primary), None)


class ProductSku(TimestampMixin, Base):
    """Price and stock live here (ADR 0002). v1 creates exactly one default SKU per product."""

    __tablename__ = "product_skus"
    __table_args__ = (
        CheckConstraint("price_minor >= 0", name="price_non_negative"),
        CheckConstraint("stock_qty >= 0", name="stock_non_negative"),
        CheckConstraint(
            "compare_at_minor IS NULL OR compare_at_minor > price_minor",
            name="compare_at_above_price",
        ),
        Index(
            "uq_product_skus_one_default",
            "product_id",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    compare_at_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProductAttribute(Base):
    __tablename__ = "product_attributes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ProductMedia(TimestampMixin, Base):
    __tablename__ = "product_media"
    __table_args__ = (
        Index(
            "uq_product_media_one_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type", native_enum=False, length=16), nullable=False
    )
    object_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    alt_text: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

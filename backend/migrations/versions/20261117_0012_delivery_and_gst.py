"""delivery charge and GST rules; GST on products and orders

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-17 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shop_charges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipping_fee_minor", sa.BigInteger(), nullable=False),
        sa.Column("free_shipping_over_minor", sa.BigInteger(), nullable=True),
        sa.Column("prices_include_gst", sa.Boolean(), nullable=False),
        sa.Column("default_gst_rate_bp", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name=op.f("ck_shop_charges_single_row")),
        sa.CheckConstraint(
            "shipping_fee_minor >= 0", name=op.f("ck_shop_charges_shipping_non_negative")
        ),
        sa.CheckConstraint(
            "free_shipping_over_minor IS NULL OR free_shipping_over_minor > 0",
            name=op.f("ck_shop_charges_free_shipping_positive"),
        ),
        sa.CheckConstraint(
            "default_gst_rate_bp BETWEEN 0 AND 4000", name=op.f("ck_shop_charges_gst_rate_range")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_shop_charges_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shop_charges")),
    )
    op.add_column("products", sa.Column("gst_rate_bp", sa.Integer(), nullable=True))
    op.create_check_constraint(
        op.f("ck_products_gst_rate_range"), "products", "gst_rate_bp BETWEEN 0 AND 4000"
    )
    op.add_column(
        "orders",
        sa.Column("gst_minor", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("prices_include_gst", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "order_items",
        sa.Column("gst_rate_bp", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "order_items",
        sa.Column("gst_minor", sa.BigInteger(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("order_items", "gst_minor")
    op.drop_column("order_items", "gst_rate_bp")
    op.drop_column("orders", "prices_include_gst")
    op.drop_column("orders", "gst_minor")
    op.drop_constraint(op.f("ck_products_gst_rate_range"), "products", type_="check")
    op.drop_column("products", "gst_rate_bp")
    op.drop_table("shop_charges")

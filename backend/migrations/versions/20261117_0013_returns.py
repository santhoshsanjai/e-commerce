"""returns and refunds

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-17 14:00:00

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = {
    "returns.view": ("View return requests", ["Super Admin", "Admin", "Manager"]),
    "returns.manage": (
        "Approve or reject returns, mark them received and record refunds",
        ["Super Admin", "Admin"],
    ),
}


def upgrade() -> None:
    op.execute("CREATE SEQUENCE return_number_seq")
    op.create_table(
        "return_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("return_number", sa.String(length=24), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("buyer_note", sa.Text(), nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=False),
        sa.Column("refund_minor", sa.BigInteger(), nullable=True),
        sa.Column("refund_method", sa.String(length=32), nullable=True),
        sa.Column("refund_reference", sa.String(length=100), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint(
            "refund_minor IS NULL OR refund_minor > 0",
            name=op.f("ck_return_requests_refund_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_return_requests_order_id_orders"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_return_requests_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["users.id"],
            name=op.f("fk_return_requests_decided_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_return_requests")),
        sa.UniqueConstraint("return_number", name=op.f("uq_return_requests_return_number")),
    )
    op.create_index(op.f("ix_return_requests_order_id"), "return_requests", ["order_id"])
    op.create_index(op.f("ix_return_requests_user_id"), "return_requests", ["user_id"])
    op.create_index(
        "ix_return_requests_status_requested_at", "return_requests", ["status", "requested_at"]
    )
    op.create_index(
        "uq_return_requests_one_open_per_order",
        "return_requests",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('REQUESTED', 'APPROVED', 'RECEIVED', 'REFUNDED')"),
    )
    op.create_table(
        "return_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("return_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("restocked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("qty > 0", name=op.f("ck_return_items_qty_positive")),
        sa.ForeignKeyConstraint(
            ["return_id"],
            ["return_requests.id"],
            name=op.f("fk_return_items_return_id_return_requests"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["order_items.id"],
            name=op.f("fk_return_items_order_item_id_order_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_return_items")),
    )
    op.create_index(op.f("ix_return_items_return_id"), "return_items", ["return_id"])

    conn = op.get_bind()
    for key, (description, roles) in PERMISSIONS.items():
        perm_id = uuid.uuid4()
        conn.execute(
            sa.text("INSERT INTO permissions (id, key, description) VALUES (:id, :key, :d)"),
            {"id": perm_id, "key": key, "d": description},
        )
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT id, :pid FROM roles WHERE name = ANY(:names) AND is_system"
            ),
            {"pid": perm_id, "names": roles},
        )


def downgrade() -> None:
    for key in PERMISSIONS:
        op.execute(
            sa.text(
                "DELETE FROM role_permissions WHERE permission_id IN "
                "(SELECT id FROM permissions WHERE key = :key)"
            ).bindparams(key=key)
        )
        op.execute(sa.text("DELETE FROM permissions WHERE key = :key").bindparams(key=key))
    op.drop_table("return_items")
    op.drop_table("return_requests")
    op.execute("DROP SEQUENCE return_number_seq")

"""storefront settings: shop name, announcement and colours

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-16 03:00:00

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION = "settings.manage"
DESCRIPTION = "Change the shop's name, announcement and colours"
GRANTED_TO = ["Super Admin", "Admin"]


def upgrade() -> None:
    op.create_table(
        "storefront_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_name", sa.String(length=60), nullable=False),
        sa.Column("announcement", sa.String(length=160), nullable=False),
        sa.Column("colors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_storefront_settings_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_storefront_settings")),
        sa.CheckConstraint("id = 1", name=op.f("ck_storefront_settings_single_row")),
    )
    conn = op.get_bind()
    perm_id = uuid.uuid4()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key, description) VALUES (:id, :key, :d)"),
        {"id": perm_id, "key": PERMISSION, "d": DESCRIPTION},
    )
    conn.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT id, :pid FROM roles WHERE name = ANY(:names) AND is_system"
        ),
        {"pid": perm_id, "names": GRANTED_TO},
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE key = :key)"
        ).bindparams(key=PERMISSION)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE key = :key").bindparams(key=PERMISSION))
    op.drop_table("storefront_settings")

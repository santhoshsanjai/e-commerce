"""shared login rate limit table

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-15 05:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_hits",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("key", sa.String(length=320), nullable=False),
        sa.Column(
            "hit_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rate_limit_hits")),
    )
    op.create_index("ix_rate_limit_hits_key_hit_at", "rate_limit_hits", ["key", "hit_at"])


def downgrade() -> None:
    op.drop_index("ix_rate_limit_hits_key_hit_at", table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")

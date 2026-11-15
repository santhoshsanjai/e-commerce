from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import get_settings
from app.infrastructure.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Every new API task runs the migrations before it starts (see the ECS task definition), so several
# can try at once during a deploy. This lock makes them take turns; later ones find nothing to do.
MIGRATION_LOCK_ID = 720_261_114


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            connection.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": MIGRATION_LOCK_ID})
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

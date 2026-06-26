"""
Alembic Migration Environment
==============================
Configures Alembic to work with SQLAlchemy 2.0+ async models
from quant_nanggroe database models.

Supports both offline (SQL script generation) and online (live migration)
modes. The async engine is used for online migrations with run_async.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from quant_nanggroe.config.settings import Settings, get_settings
from quant_nanggroe.database.models import Base

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# ── Logging Setup ───────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── MetaData Target ─────────────────────────────────────────────────
# This is the MetaData object that Autogenerate will compare against.
target_metadata = Base.metadata

# ── Override sqlalchemy.url from settings ───────────────────────────
# Use the sync URL for migrations (Alembic runs synchronously for offline mode,
# but we use the async engine for online mode via run_async).
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.db.sync_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to a database.
    Useful for CI/CD pipelines and review processes.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Execute migrations using a provided connection.

    This function is called both in sync and async contexts.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        # Compare types for accurate change detection
        compare_type=True,
        # Include name-based naming conventions
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations using an async engine.

    Creates an async engine from Alembic config, connects,
    and runs migrations within the async context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.db.url,  # Use async URL
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Uses async engine to connect to the database and apply migrations.
    Falls back to sync engine if async fails.
    """
    try:
        asyncio.run(run_async_migrations())
    except Exception as exc:
        # Fallback: try sync engine (for environments where asyncpg is not available)
        import logging
        logging.getLogger(__name__).warning(
            f"Async migration failed, attempting sync fallback: {exc}"
        )
        from sqlalchemy import engine_from_config

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            do_run_migrations(connection)

        connectable.dispose()


# ── Entry Point ─────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

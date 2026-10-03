"""Minimal Alembic environment for the example application.

Wired the same way as production: the migration scripts import the models via
the application's own package, which is why the CI job sets PYTHONPATH=.
Running `alembic` (a console script) does not put the working directory on
sys.path the way `python some_script.py` does. Without PYTHONPATH, the import
of `app` below fails with ModuleNotFoundError.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.main import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The URL is never committed to alembic.ini. It comes from the environment:
# the CI job passes a throwaway Postgres URL, production passes the real one.
# Failing loudly here beats a confusing "Connection, url, or dialect_name is
# required" from deep inside Alembic when the variable is missing.
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Alembic reads its connection URL from the "
        "environment — see alembic.ini's empty sqlalchemy.url and this file."
    )
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

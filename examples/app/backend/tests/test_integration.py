"""Integration test — run by Gate 2 against a real Postgres database.

The database is created by the CI job (a throwaway Postgres service), migrated
by Alembic, then exercised here. This is the test that catches anything
Postgres-specific which the in-memory suite in test_unit.py quietly tolerates.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import Item

DATABASE_URL = __import__("os").environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_DATABASE_URL not set — integration suite only runs under CI.",
)


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine(DATABASE_URL, future=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_migrations_created_the_items_table(session: AsyncSession) -> None:
    """The table must exist because a migration created it, not because the
    app auto-created it. If this fails, migrations did not run."""
    result = await session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'items' ORDER BY ordinal_position"
        )
    )
    columns = [row[0] for row in result]
    assert columns == ["id", "name", "created_at"], f"unexpected schema: {columns}"


async def test_alembic_is_at_head(session: AsyncSession) -> None:
    """Guards against a migration that failed silently and left the database
    behind the latest revision."""
    result = await session.execute(text("SELECT version_num FROM alembic_version"))
    revisions = [row[0] for row in result]
    assert len(revisions) == 1, f"expected exactly one head, got {revisions}"


async def test_insert_and_read_back(session: AsyncSession) -> None:
    item = Item(name="integration-test-row")
    session.add(item)
    await session.commit()

    result = await session.execute(text("SELECT name FROM items WHERE name = :n"), {"n": item.name})
    assert result.scalar_one() == "integration-test-row"

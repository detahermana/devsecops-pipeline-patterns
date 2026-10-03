"""Minimal example application for the pipeline templates to run against.

Deliberately small: the point of this repository is the pipeline, not the app.
It has just enough surface to make each gate meaningful — a route to test, a
database to migrate, and a table to read.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, FastAPI
from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

app = FastAPI(title="Pipeline Example API", version="1.0.0")


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


async def get_session() -> AsyncSession:
    """Placeholder session dependency.

    The real application wires this to an async engine. Kept trivial here so
    the example has no hard dependency on a running database for import.
    """
    raise NotImplementedError("Wire this to your session factory.")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Used by the deployment step's readiness check."""
    return {"status": "ok"}


@app.get("/items")
async def list_items(session: AsyncSession = Depends(get_session)) -> list[dict[str, object]]:
    """Read endpoint — the integration test exercises this against real Postgres."""
    result = await session.execute(select(Item).order_by(Item.id))
    return [
        {"id": row.id, "name": row.name, "created_at": row.created_at.isoformat()}
        for row in result.scalars()
    ]


def add(a: int, b: int) -> int:
    """Pure function with a unit test — keeps Gate 1 honest."""
    return a + b

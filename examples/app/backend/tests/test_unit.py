"""Unit tests — run by Gate 1 against an in-memory database.

These must stay fast and dependency-free. Anything that needs real Postgres
belongs in the integration suite that Gate 2 runs.
"""

from __future__ import annotations

from app.main import add


def test_add_positive() -> None:
    assert add(2, 3) == 5


def test_add_negative() -> None:
    assert add(-4, 1) == -3


def test_add_zero() -> None:
    assert add(0, 7) == 7

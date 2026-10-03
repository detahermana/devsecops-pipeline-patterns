"""Create the items table.

Revision ID: 0001
Revises:
Create Date: 2026-01-01

NOTE ON REVISION ID LENGTH — the reason this file carries a warning.

alembic_version.version_num is VARCHAR(32). A revision identifier longer than
32 characters fails the INSERT into that table, and in most setups the failure
does not abort loudly — `alembic upgrade head` appears to complete, the schema
change rolls back, and the database stays at the previous revision. This
exact failure caused a production incident; Gate 2 in the pipeline now
verifies the database actually landed on the migration head for precisely
this reason. See docs/incident-regression.md.

Keep revision IDs short.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("items")

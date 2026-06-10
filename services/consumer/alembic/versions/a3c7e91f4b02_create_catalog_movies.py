"""Create catalog_movies table for API-managed movie catalog.

Revision ID: a3c7e91f4b02
Revises: d4e8f1a92b03
Create Date: 2026-06-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3c7e91f4b02"
down_revision: Union[str, Sequence[str], None] = "d4e8f1a92b03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_movies",
        sa.Column("movie_id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "genres",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "pending_opensearch_sync",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("synced_to_opensearch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "pipeline_version",
            sa.Text(),
            server_default="v1",
            nullable=False,
        ),
    )
    op.create_index(
        "idx_catalog_movies_pending_sync",
        "catalog_movies",
        ["pending_opensearch_sync"],
    )


def downgrade() -> None:
    op.drop_index("idx_catalog_movies_pending_sync", table_name="catalog_movies")
    op.drop_table("catalog_movies")

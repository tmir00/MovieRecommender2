"""Add TMDB enrichment columns to catalog_movies.

Revision ID: e8f2a41c9d05
Revises: a3c7e91f4b02
Create Date: 2026-06-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e8f2a41c9d05"
down_revision: Union[str, Sequence[str], None] = "a3c7e91f4b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("catalog_movies", sa.Column("tmdb_id", sa.Integer(), nullable=True))
    op.add_column("catalog_movies", sa.Column("overview", sa.Text(), nullable=True))
    op.add_column("catalog_movies", sa.Column("tagline", sa.Text(), nullable=True))
    op.add_column(
        "catalog_movies",
        sa.Column(
            "tmdb_keywords",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column(
        "catalog_movies",
        sa.Column("popularity", sa.Float(), nullable=True),
    )
    op.add_column(
        "catalog_movies",
        sa.Column("vote_average", sa.Float(), nullable=True),
    )
    op.add_column("catalog_movies", sa.Column("vote_count", sa.Integer(), nullable=True))
    op.add_column("catalog_movies", sa.Column("runtime", sa.Integer(), nullable=True))
    op.add_column(
        "catalog_movies",
        sa.Column("original_language", sa.Text(), nullable=True),
    )
    op.add_column("catalog_movies", sa.Column("release_date", sa.Text(), nullable=True))
    op.add_column(
        "catalog_movies",
        sa.Column("tmdb_enriched_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "idx_catalog_movies_tmdb_id",
        "catalog_movies",
        ["tmdb_id"],
        postgresql_where=sa.text("tmdb_id IS NOT NULL"),
    )
    op.create_index(
        "idx_catalog_movies_tmdb_enrich_pending",
        "catalog_movies",
        ["tmdb_enriched_at"],
        postgresql_where=sa.text(
            "tmdb_id IS NOT NULL AND tmdb_enriched_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_catalog_movies_tmdb_enrich_pending",
        table_name="catalog_movies",
    )
    op.drop_index("idx_catalog_movies_tmdb_id", table_name="catalog_movies")
    op.drop_column("catalog_movies", "tmdb_enriched_at")
    op.drop_column("catalog_movies", "release_date")
    op.drop_column("catalog_movies", "original_language")
    op.drop_column("catalog_movies", "runtime")
    op.drop_column("catalog_movies", "vote_count")
    op.drop_column("catalog_movies", "vote_average")
    op.drop_column("catalog_movies", "popularity")
    op.drop_column("catalog_movies", "tmdb_keywords")
    op.drop_column("catalog_movies", "tagline")
    op.drop_column("catalog_movies", "overview")
    op.drop_column("catalog_movies", "tmdb_id")

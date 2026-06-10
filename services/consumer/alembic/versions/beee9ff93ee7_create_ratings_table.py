"""Create ratings_events and tag_events tables.

Each row is one event we consumed from Kafka and stored for querying later.
Revision ID: beee9ff93ee7
Revises:
Create Date: 2026-06-02 15:41:19.393243

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "beee9ff93ee7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema changes: create tables and indexes."""

    # --- Ratings (one row per rating event) ---
    op.create_table(
        "ratings_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False),
        sa.Column("rating_timestamp", sa.BigInteger(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_file", sa.Text(), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column(
            "pipeline_version",
            sa.Text(),
            server_default="v1",
            nullable=False,
        ),
    )

    # Create indexes on the ratings events table.
    op.create_index("idx_ratings_user_id", "ratings_events", ["user_id"])
    op.create_index("idx_ratings_movie_id", "ratings_events", ["movie_id"])
    op.create_index("idx_ratings_timestamp", "ratings_events", ["rating_timestamp"])

    # --- Tags (one row per tag event) ---
    op.create_table(
        "tag_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.Text(), nullable=False),
        sa.Column("tag_timestamp", sa.BigInteger(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_file", sa.Text(), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column(
            "pipeline_version",
            sa.Text(),
            server_default="v1",
            nullable=False,
        ),
    )
    # Create indexes on the tags events table.
    op.create_index("idx_tags_user_id", "tag_events", ["user_id"])
    op.create_index("idx_tags_movie_id", "tag_events", ["movie_id"])
    op.create_index("idx_tags_timestamp", "tag_events", ["tag_timestamp"])


def downgrade() -> None:
    """Undo upgrade: drop indexes and tables (reverse order)."""

    op.drop_index("idx_tags_timestamp", table_name="tag_events")
    op.drop_index("idx_tags_movie_id", table_name="tag_events")
    op.drop_index("idx_tags_user_id", table_name="tag_events")
    op.drop_table("tag_events")

    op.drop_index("idx_ratings_timestamp", table_name="ratings_events")
    op.drop_index("idx_ratings_movie_id", table_name="ratings_events")
    op.drop_index("idx_ratings_user_id", table_name="ratings_events")
    op.drop_table("ratings_events")

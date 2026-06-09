"""SQLAlchemy Core table definitions (must stay in sync with Alembic migrations in consumer/alembic)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY

metadata = MetaData()

ratings_events = Table(
    "ratings_events",
    metadata,
    Column("event_id", Text, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("movie_id", Integer, nullable=False),
    Column("rating", Numeric(2, 1), nullable=False),
    Column("rating_timestamp", BigInteger, nullable=False),
    Column(
        "ingested_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
    Column("source_file", Text, nullable=True),
    Column("source_row_number", Integer, nullable=True),
    Column("pipeline_version", Text, server_default="v1", nullable=False),
)

tag_events = Table(
    "tag_events",
    metadata,
    Column("event_id", Text, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("movie_id", Integer, nullable=False),
    Column("tag", Text, nullable=False),
    Column("tag_timestamp", BigInteger, nullable=False),
    Column(
        "ingested_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
    Column("source_file", Text, nullable=True),
    Column("source_row_number", Integer, nullable=True),
    Column("pipeline_version", Text, server_default="v1", nullable=False),
)

dead_letter_events = Table(
    "dead_letter_events",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("source_topic", Text, nullable=False),
    Column("source_partition", Integer, nullable=False),
    Column("source_offset", BigInteger, nullable=False),
    Column("consumer_group", Text, nullable=False),
    Column("error_type", Text, nullable=False),
    Column("error_message", Text, nullable=False),
    Column("payload", Text, nullable=True),
    Column(
        "failed_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
    Column("resolved", Boolean, server_default=false(), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    Column("resolution_notes", Text, nullable=True),
)

catalog_movies = Table(
    "catalog_movies",
    metadata,
    Column("movie_id", Integer, primary_key=True),
    Column("title", Text, nullable=False),
    Column("genres", ARRAY(Text), nullable=False),
    Column("year", Integer, nullable=True),
    Column("tags", ARRAY(Text), nullable=False),
    Column("active", Boolean, nullable=False),
    Column("pending_opensearch_sync", Boolean, nullable=False),
    Column("synced_to_opensearch_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("pipeline_version", Text, nullable=False),
    Column("tmdb_id", Integer, nullable=True),
    Column("overview", Text, nullable=True),
    Column("tagline", Text, nullable=True),
    Column("tmdb_keywords", ARRAY(Text), nullable=False),
    Column("popularity", Float, nullable=True),
    Column("vote_average", Float, nullable=True),
    Column("vote_count", Integer, nullable=True),
    Column("runtime", Integer, nullable=True),
    Column("original_language", Text, nullable=True),
    Column("release_date", Text, nullable=True),
    Column("tmdb_enriched_at", DateTime(timezone=True), nullable=True),
)

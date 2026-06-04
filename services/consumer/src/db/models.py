"""SQLAlchemy Core table definitions (must stay in sync with Alembic migrations)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    false,
    func,
)

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

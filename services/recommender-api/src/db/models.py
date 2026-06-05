"""Catalog table definition (keep in sync with consumer db/models.py)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    Text,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY

metadata = MetaData()

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
)

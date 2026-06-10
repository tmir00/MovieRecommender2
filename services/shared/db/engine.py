"""SQLAlchemy engine factory shared across services."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def create_engine_from_url(database_url: str, *, pool_pre_ping: bool = True) -> Engine:
    """
    Create a SQLAlchemy engine from a database URL.

    ============================ Arguments ============================
    database_url: Postgres connection URL (e.g. postgresql+psycopg://...).
    pool_pre_ping: When True, test connections before use from the pool.

    ============================ Returns ============================
    A configured SQLAlchemy engine with a connection pool.
    """
    return create_engine(database_url, pool_pre_ping=pool_pre_ping)

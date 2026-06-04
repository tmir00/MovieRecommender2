"""Database engine (SQLAlchemy Core)."""

import os

from sqlalchemy import create_engine


def get_engine():
    """
    Create a SQLAlchemy engine from DATABASE_URL.

    ==================== Returns ====================
    A configured SQLAlchemy engine with a connection pool.
    """
    database_url = os.environ["DATABASE_URL"]
    return create_engine(database_url, pool_pre_ping=True)

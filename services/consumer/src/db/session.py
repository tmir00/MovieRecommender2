"""Database engine (SQLAlchemy Core)."""

import os

from shared.db.engine import create_engine_from_url


def get_engine():
    """
    Create a SQLAlchemy engine from DATABASE_URL.

    ==================== Returns ====================
    A configured SQLAlchemy engine with a connection pool.
    """
    database_url = os.environ["DATABASE_URL"]
    return create_engine_from_url(database_url)

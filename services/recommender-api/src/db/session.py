"""
Here we create the SQLAlchemy engine that will be used to interact with the database.
This is used by the recommender API to read from the database when we need to query the catalog.
"""

import os

from sqlalchemy.engine import Engine

from shared.db.engine import create_engine_from_url


def get_engine() -> Engine:
    """
    Create a SQLAlchemy engine from DATABASE_URL.

    ==================== Returns ====================
    A configured SQLAlchemy engine with a connection pool.
    """
    database_url = os.environ["DATABASE_URL"]
    return create_engine_from_url(database_url)

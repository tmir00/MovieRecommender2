"""Postgres connectivity checks shared across services."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ping_postgres(engine: Engine) -> bool:
    """
    Connect to the database and execute a simple query to check if it is reachable.

    ============================ Returns ============================
    True if the database is reachable, False otherwise.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

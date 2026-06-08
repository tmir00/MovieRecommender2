"""Catalog movie reads and writes against catalog_movies (SQLAlchemy Core)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, func, insert, select, text
from sqlalchemy.engine import Engine

from shared.db.models import catalog_movies
from shared.exceptions import CatalogMovieAlreadyExists
from shared.movie_document import parse_title_year


# SQL query to find all the movies that are pending sync to the OpenSearch cluster.
_PENDING_SELECT = text(
    """
    SELECT movie_id, title, genres, year, tags, pipeline_version
    FROM catalog_movies
    WHERE pending_opensearch_sync = true AND active = true
    ORDER BY movie_id
    LIMIT :batch_size
    """
)

# SQL query to mark the movies as synced to the OpenSearch cluster.
_MARK_SYNCED = (
    text(
        """
    UPDATE catalog_movies
    SET pending_opensearch_sync = false,
        synced_to_opensearch_at = NOW(),
        updated_at = NOW()
    WHERE movie_id IN :movie_ids
    """
    ).bindparams(bindparam("movie_ids", expanding=True))
)


def _resolve_year(title: str, explicit_year: int | None) -> int | None:
    if explicit_year is not None:
        return explicit_year
    _, parsed = parse_title_year(title)
    return parsed


def _next_movie_id(engine: Engine) -> int:
    with engine.connect() as conn:
        result = conn.execute(select(func.coalesce(func.max(catalog_movies.c.movie_id), 0)))
        current_max = result.scalar_one()
        return int(current_max) + 1


def insert_catalog_movie(engine: Engine, *, movie_id: int | None, title: str, genres: list[str], \
                            year: int | None, pipeline_version: str) -> tuple[int, int | None]:
    """
    Insert one movie into catalog_movies.

    1. Resolve movie_id (allocate next id when movie_id is None).
    2. Resolve year from the title when year is not provided.
    3. Insert the row with pending_opensearch_sync=true.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    movie_id: Optional explicit movie_id; when None, the next id is allocated.
    title: Movie title.
    genres: Movie genres.
    year: Optional explicit year; parsed from title when None.
    pipeline_version: Pipeline label stored on the row (e.g. v1).

    ============================ Returns ============================
    A tuple of (movie_id, resolved_year).
    """
    resolved_movie_id = movie_id if movie_id is not None else _next_movie_id(engine)
    resolved_year = _resolve_year(title, year)

    with engine.begin() as conn:
        existing = conn.execute(
            select(catalog_movies.c.movie_id).where(
                catalog_movies.c.movie_id == resolved_movie_id
            )
        ).first()
        if existing is not None:
            raise CatalogMovieAlreadyExists(resolved_movie_id)

        conn.execute(
            insert(catalog_movies).values(
                movie_id=resolved_movie_id,
                title=title,
                genres=genres,
                year=resolved_year,
                tags=[],
                active=True,
                pending_opensearch_sync=True,
                pipeline_version=pipeline_version,
            )
        )

    return resolved_movie_id, resolved_year


def fetch_catalog_movie_by_id(engine: Engine, movie_id: int) -> dict[str, Any] | None:
    """
    Fetch one catalog movie row by movie_id.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    movie_id: The movie id to look up.

    ============================ Returns ============================
    A row mapping (movie_id, title, genres, year, tags, pipeline_version), 
    or None if not found.
    """
    with engine.connect() as conn:
        row = conn.execute(
            select(
                catalog_movies.c.movie_id,
                catalog_movies.c.title,
                catalog_movies.c.genres,
                catalog_movies.c.year,
                catalog_movies.c.tags,
                catalog_movies.c.pipeline_version,
            ).where(catalog_movies.c.movie_id == movie_id)
        ).mappings().first()
    if row is None:
        return None
    return dict(row)


def fetch_pending_catalog_movies(engine: Engine, *, batch_size: int) -> list[Any]:
    """
    Fetch a batch of catalog rows pending sync to OpenSearch.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    batch_size: Maximum number of rows to return.

    ============================ Returns ============================
    A list of row mappings (movie_id, title, genres, year, tags, pipeline_version).
    """
    with engine.connect() as conn:
        # Fetch the pending catalog rows from the database in batches.
        rows = conn.execute(
            _PENDING_SELECT,
            {"batch_size": batch_size},
        ).mappings().all()
    return list(rows)


def mark_catalog_movies_synced(engine: Engine, movie_ids: list[int]) -> None:
    """
    Mark catalog movies as synced to OpenSearch.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    movie_ids: Movie ids to mark as synced.
    """
    if not movie_ids:
        return

    with engine.begin() as conn:
        conn.execute(_MARK_SYNCED, {"movie_ids": movie_ids})


def count_pending_catalog_sync(engine: Engine) -> int:
    """
    Count active catalog movies pending sync to OpenSearch.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.

    ============================ Returns ============================
    The number of movies with pending_opensearch_sync=true and active=true.
    """
    with engine.connect() as conn:
        result = conn.execute(
            select(func.count())
            .select_from(catalog_movies)
            .where(
                catalog_movies.c.pending_opensearch_sync.is_(True),
                catalog_movies.c.active.is_(True),
            )
        )
        return int(result.scalar_one())

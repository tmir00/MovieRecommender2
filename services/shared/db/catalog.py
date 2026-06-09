"""Catalog movie reads and writes against catalog_movies (SQLAlchemy Core)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, func, insert, select, text
from sqlalchemy.engine import Engine

from shared.db.models import catalog_movies
from shared.features.models import TmdbMetadata
from shared.features.parsers import resolve_year
from shared.exceptions import CatalogMovieAlreadyExists
from shared.tmdb.models import catalog_tmdb_update_values


_CATALOG_COLUMNS_SQL = """
    movie_id, title, genres, year, tags, pipeline_version,
    tmdb_id, overview, tagline, tmdb_keywords,
    popularity, vote_average, vote_count, runtime,
    original_language, release_date, tmdb_enriched_at
"""

# SQL query to find all the movies that are pending sync to the OpenSearch cluster.
_PENDING_SELECT = text(
    f"""
    SELECT {_CATALOG_COLUMNS_SQL}
    FROM catalog_movies
    WHERE pending_opensearch_sync = true AND active = true
    ORDER BY movie_id
    LIMIT :batch_size
    """
)

# SQL query to fetch all the active catalog movies.
_ACTIVE_CATALOG_SELECT = text(
    f"""
    SELECT {_CATALOG_COLUMNS_SQL}
    FROM catalog_movies
    WHERE active = true
      AND movie_id > :after_movie_id
    ORDER BY movie_id
    LIMIT :batch_size
    """
)

# SQL query to fetch all the catalog movies that need TMDB enrichment.
_TMDB_ENRICH_SELECT = text(
    """
    SELECT movie_id, tmdb_id
    FROM catalog_movies
    WHERE tmdb_id IS NOT NULL
      AND tmdb_enriched_at IS NULL
      AND movie_id > :after_movie_id
    ORDER BY movie_id
    LIMIT :batch_size
    """
)

# SQL query to upsert a catalog movie.
_UPSERT_CATALOG_MOVIE = text(
    """
    INSERT INTO catalog_movies (
        movie_id, title, genres, year, tags, active,
        pending_opensearch_sync, pipeline_version, tmdb_id,
        created_at, updated_at
    )
    VALUES (
        :movie_id, :title, :genres, :year, '{}', true,
        true, :pipeline_version, :tmdb_id,
        NOW(), NOW()
    )
    ON CONFLICT (movie_id) DO UPDATE SET
        title = EXCLUDED.title,
        genres = EXCLUDED.genres,
        year = EXCLUDED.year,
        tmdb_id = EXCLUDED.tmdb_id,
        updated_at = NOW(),
        pending_opensearch_sync = CASE
            WHEN catalog_movies.title IS DISTINCT FROM EXCLUDED.title
              OR catalog_movies.genres IS DISTINCT FROM EXCLUDED.genres
              OR catalog_movies.year IS DISTINCT FROM EXCLUDED.year
              OR catalog_movies.tmdb_id IS DISTINCT FROM EXCLUDED.tmdb_id
            THEN true
            ELSE catalog_movies.pending_opensearch_sync
        END
    """
)

# SQL query to update the TMDB metadata for a catalog movie.
_UPDATE_TMDB_METADATA = text(
    """
    UPDATE catalog_movies
    SET overview = :overview,
        tagline = :tagline,
        tmdb_keywords = :tmdb_keywords,
        popularity = :popularity,
        vote_average = :vote_average,
        vote_count = :vote_count,
        runtime = :runtime,
        original_language = :original_language,
        release_date = :release_date,
        tmdb_enriched_at = NOW(),
        updated_at = NOW(),
        pending_opensearch_sync = true
    WHERE movie_id = :movie_id
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


def _catalog_select_columns():
    """Column list for single-row fetch by movie_id."""
    return [
        catalog_movies.c.movie_id,
        catalog_movies.c.title,
        catalog_movies.c.genres,
        catalog_movies.c.year,
        catalog_movies.c.tags,
        catalog_movies.c.pipeline_version,
        catalog_movies.c.tmdb_id,
        catalog_movies.c.overview,
        catalog_movies.c.tagline,
        catalog_movies.c.tmdb_keywords,
        catalog_movies.c.popularity,
        catalog_movies.c.vote_average,
        catalog_movies.c.vote_count,
        catalog_movies.c.runtime,
        catalog_movies.c.original_language,
        catalog_movies.c.release_date,
        catalog_movies.c.tmdb_enriched_at,
    ]


def _next_movie_id(engine: Engine) -> int:
    """

    "Fetch the next movie_id from the catalog_movies table.
    Example:
        SELECT MAX(movie_id) + 1 FROM catalog_movies;

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.

    ============================ Returns ============================
    The next movie_id.
    """
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
    # Resolve the movie_id and year.
    resolved_movie_id = movie_id if movie_id is not None else _next_movie_id(engine)
    resolved_year = resolve_year(title, year)

    # Check if the movie already exists.
    with engine.begin() as conn:
        existing = conn.execute(
            select(catalog_movies.c.movie_id).where(
                catalog_movies.c.movie_id == resolved_movie_id
            )
        ).first()
        # If the movie already exists, raise an exception.
        if existing is not None:
            raise CatalogMovieAlreadyExists(resolved_movie_id)

        # Insert the movie into the catalog_movies table.
        conn.execute(
            insert(catalog_movies).values(
                movie_id=resolved_movie_id,
                title=title,
                genres=genres,
                year=resolved_year,
                tags=[],
                tmdb_keywords=[],
                active=True,
                pending_opensearch_sync=True,
                pipeline_version=pipeline_version,
            )
        )

    return resolved_movie_id, resolved_year


def upsert_catalog_movies_batch(engine: Engine, rows: list[dict[str, Any]], *, pipeline_version: str) -> int:
    """
    Bulk upsert ML-25m seed rows into catalog_movies.

    Do this by:
    1. Building one upsert statement per row.
    2. Inserting new rows with pending_opensearch_sync=true.
    3. On conflict, updating catalog fields only and marking pending when they change.

    TMDB columns are never overwritten by the seed job.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    rows: Seed rows with movie_id, title, genres, year, tmdb_id.
    pipeline_version: Pipeline label stored on new rows.

    ============================ Returns ============================
    Number of rows processed.
    """
    # If there are no rows to upsert, return 0.
    if not rows:
        return 0

    # Build the parameters for the upsert statement.
    params = [
        {
            "movie_id": row["movie_id"],
            "title": row["title"],
            "genres": row["genres"],
            "year": row["year"],
            "tmdb_id": row.get("tmdb_id"),
            "pipeline_version": pipeline_version,
        }
        for row in rows
    ]

    # Execute the upsert statement.
    with engine.begin() as conn:
        conn.execute(_UPSERT_CATALOG_MOVIE, params)

    return len(params)


def fetch_catalog_movie_by_id(engine: Engine, movie_id: int) -> dict[str, Any] | None:
    """
    Fetch one catalog movie row by movie_id from the postgres database.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    movie_id: The movie id to look up.

    ============================ Returns ============================
    Returns a dictionary of one movie’s Postgres columns 
    (catalog + TMDB), or None if that movie_id doesn’t exist.
    
    E.g: 
    {
        "movie_id": 1,
        "title": "The Matrix",
        "genres": ["Action", "Sci-Fi"],
        "year": 1999,
        "tags": [],
        "pipeline_version": "v1",
    }
    """
    # Fetch the catalog movie row by movie_id.
    with engine.connect() as conn:
        row = conn.execute(
            select(*_catalog_select_columns()).where(
                catalog_movies.c.movie_id == movie_id
            )
        ).mappings().first()
    # If the movie is not found, return None.
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
    A list of row mappings that need to be indexed into OpenSearch.
    """
    with engine.connect() as conn:
        # Fetch the pending catalog rows from the database in batches.
        rows = conn.execute(
            _PENDING_SELECT,
            {"batch_size": batch_size},
        ).mappings().all()
    return list(rows)


def fetch_active_catalog_movies_batch(engine: Engine, *, batch_size: int, \
                                        after_movie_id: int = 0) -> list[dict[str, Any]]:
    """
    Fetch the next batch of active catalog rows for bootstrap indexing.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    batch_size: Maximum number of rows to return.
    after_movie_id: Return rows with movie_id greater than this cursor.

    ============================ Returns ============================
    Ordered row mappings with base and TMDB columns.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            _ACTIVE_CATALOG_SELECT,
            {"batch_size": batch_size, "after_movie_id": after_movie_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def fetch_rows_needing_tmdb_enrichment(engine: Engine, *, batch_size: int, \
                                        after_movie_id: int = 0) -> list[dict[str, Any]]:
    """
    Fetch catalog rows that have tmdb_id but no enrichment timestamp yet.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    batch_size: Maximum number of rows to return.
    after_movie_id: Return rows with movie_id greater than this cursor.

    ============================ Returns ============================
    Row mappings with movie_id and tmdb_id.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            _TMDB_ENRICH_SELECT,
            {"batch_size": batch_size, "after_movie_id": after_movie_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def update_catalog_tmdb_metadata(engine: Engine, movie_id: int, metadata: TmdbMetadata) -> None:
    """
    Write TMDB enrichment fields to one catalog_movies row.

    Sets tmdb_enriched_at and pending_opensearch_sync so index jobs pick up new text.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    movie_id: Catalog movie id to update.
    metadata: TMDB metadata from the API.
    """
    values = catalog_tmdb_update_values(metadata)
    values["movie_id"] = movie_id

    with engine.begin() as conn:
        conn.execute(_UPDATE_TMDB_METADATA, values)


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


def count_active_catalog_movies(engine: Engine) -> int:
    """
    Count active rows in catalog_movies.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.

    ============================ Returns ============================
    Number of rows with active=true.
    """
    with engine.connect() as conn:
        result = conn.execute(
            select(func.count())
            .select_from(catalog_movies)
            .where(catalog_movies.c.active.is_(True))
        )
        return int(result.scalar_one())


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

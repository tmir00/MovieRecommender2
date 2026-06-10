"""Read tag_events and roll up top user tags into catalog_movies."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy import func, select, text

from shared.db.models import tag_events


# SQL query that takes all user-submitted tags, counts how
# often each tag appears by movie, ranks them by count and 
# then alphabetically (tiebreaker), and then returns the top 
# N tags per movie.
#
# E.g: Returns:
# movie_id | tags
# ---------|-------------------------------
# 1        | {"funny", "classic", "pixar"}
# 2        | {"dark", "sci-fi", "mind-bending"}
# 3        | {"romance", "slow", "emotional"}
_AGGREGATE_TOP_TAGS = text(
    """
    WITH tag_counts AS (
        SELECT
            movie_id,
            lower(trim(tag)) AS tag,
            COUNT(*) AS cnt
        FROM tag_events
        WHERE lower(trim(tag)) <> ''
        GROUP BY movie_id, lower(trim(tag))
    ),
    ranked AS (
        SELECT
            movie_id,
            tag,
            ROW_NUMBER() OVER (
                PARTITION BY movie_id
                ORDER BY cnt DESC, tag
            ) AS rn
        FROM tag_counts
    )
    SELECT
        movie_id,
        array_agg(tag ORDER BY rn) AS tags
    FROM ranked
    WHERE rn <= :top_n
    GROUP BY movie_id
    ORDER BY movie_id
    """
)


# SQL query that updates the catalog_movies table with the new tags
# and marks the movie as pending_opensearch_sync if the tags changed.
_UPDATE_CATALOG_TAGS = text(
    """
    UPDATE catalog_movies
    SET tags = :new_tags,
        pending_opensearch_sync = CASE
            WHEN catalog_movies.tags IS DISTINCT FROM :new_tags THEN true
            ELSE catalog_movies.pending_opensearch_sync
        END,
        updated_at = NOW()
    WHERE movie_id = :movie_id
    """
)


def count_tag_events(engine: Engine) -> int:
    """
    Count the number of tag events in the tag_events table.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.

    ============================ Returns ============================
    Number of tag event rows in Postgres.
    """
    with engine.connect() as conn:
        result = conn.execute(select(func.count()).select_from(tag_events))
        return int(result.scalar_one())


def aggregate_top_tags_by_movie(engine: Engine, *, top_n: int) -> list[dict[str, Any]]:
    """
    Build the most common user tags per movie from tag_events.
    This returns the 'rolled up' tags for each movie.

    Do this by:
    1. Normalizing tag text (lowercase, trim whitespace).
    2. Counting how often each tag appears per movie.
    3. Keeping the top N tags per movie, with ties broken alphabetically.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    top_n: Maximum number of distinct tags to keep per movie.

    ============================ Returns ============================
    List of dicts with movie_id and tags (ordered most common first).
    This is the 'rolled up' tags for each movie.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            _AGGREGATE_TOP_TAGS,
            {"top_n": top_n},
        ).mappings().all()

    return [
        {
            "movie_id": int(row["movie_id"]),
            "tags": list(row["tags"] or []),
        }
        for row in rows
    ]


def apply_tag_rollup_to_catalog(engine: Engine, rollup_rows: list[dict[str, Any]], *, batch_size: int) -> dict[str, int]:
    """
    Write rolled-up tags onto catalog_movies rows that already exist.

    Do this by:
    1. Updating catalog_movies.tags for each movie in the rollup.
    2. Setting pending_opensearch_sync=true only when the tag list changed.
    3. Skipping movie ids that are not in catalog_movies.

    ============================ Arguments ============================
    engine: The SQLAlchemy engine.
    rollup_rows: Output from aggregate_top_tags_by_movie.
    batch_size: How many movies to update per database transaction.

    ============================ Returns ============================
    Counts for movies_in_rollup, movies_updated, movies_marked_pending,
    and movies_skipped_not_in_catalog.
    """
    movies_in_rollup = len(rollup_rows)
    movies_updated = 0
    movies_marked_pending = 0

    # If there are no rollup rows, return 0 for all counts.
    if not rollup_rows:
        return {
            "movies_in_rollup": 0,
            "movies_updated": 0,
            "movies_marked_pending": 0,
            "movies_skipped_not_in_catalog": 0,
        }

    # Loop through the rollup rows in batches and update the catalog_movies table.
    for start in range(0, len(rollup_rows), batch_size):
        # Get the next batch of rollup rows.
        batch = rollup_rows[start : start + batch_size]
        # Get the movie ids for the next batch of rollup rows.
        movie_ids = [row["movie_id"] for row in batch]

        # Fetch the existing tags in catalog_movies in postgres for the movie ids in the batch.
        with engine.connect() as conn:
            existing_rows = conn.execute(
                text(
                    """
                    SELECT movie_id, tags
                    FROM catalog_movies
                    WHERE movie_id = ANY(:movie_ids)
                    """
                ),
                {"movie_ids": movie_ids},
            ).mappings().all()

        # Create a dictionary of existing tags by movie id.
        existing_by_id = {
            int(row["movie_id"]): list(row["tags"] or [])
            for row in existing_rows
        }

        # Create a list of parameters for the update statement.
        params = []
        # Loop through the batch of rollup rows and check if the tags changed.
        for row in batch:
            movie_id = int(row["movie_id"])
            # If the movie id is not in the existing tags, skip it.
            if movie_id not in existing_by_id:
                continue

            # Get the new tags for the movie.
            new_tags = list(row["tags"] or [])
            # If the new tags are different from the existing tags, mark the movie as pending_opensearch_sync.
            if existing_by_id[movie_id] != new_tags:
                movies_marked_pending += 1

            # Add the movie id and new tags to the parameters list.
            # This will be used to update the catalog_movies table.
            params.append(
                {
                    "movie_id": movie_id,
                    "new_tags": new_tags,
                }
            )

        # If there are no parameters, skip the batch.
        if not params:
            continue

        # Execute the update statement for the batch of parameters.
        with engine.begin() as conn:
            for param in params:
                result = conn.execute(_UPDATE_CATALOG_TAGS, param)
                movies_updated += int(result.rowcount or 0)
                
    # Calculate the number of movies skipped because they are not in the catalog.
    movies_skipped_not_in_catalog = movies_in_rollup - movies_updated

    return {
        "movies_in_rollup": movies_in_rollup,
        "movies_updated": movies_updated,
        "movies_marked_pending": movies_marked_pending,
        "movies_skipped_not_in_catalog": movies_skipped_not_in_catalog,
    }

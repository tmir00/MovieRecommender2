"""Fetch TMDB metadata and store enrichment on catalog_movies in Postgres."""

from __future__ import annotations

import os
import sys
import time
import logging

from shared.db.catalog import (
    fetch_rows_needing_tmdb_enrichment,
    update_catalog_tmdb_metadata,
)
from shared.db.engine import create_engine_from_url
from shared.logging_config import configure_logging
from shared.tmdb.client import TmdbClient
from shared.tmdb.config import TmdbConfig


def enrich_tmdb(config: TmdbConfig, logger: logging.Logger) -> dict[str, int]:
    """
    Populate catalog_movies with TMDB metadata from the TMDB API.

    Do this by:
    1. Querying Postgres for rows with tmdb_id but no tmdb_enriched_at.
    2. Fetching each movie from TMDB with rate limiting.
    3. Updating catalog_movies with TMDB columns and pending_opensearch_sync=true.

    ============================ Arguments ============================
    config: TMDB and Postgres configuration.
    logger: Logger for progress and summary output.

    ============================ Returns ============================
    Counts for processed, fetched, skipped_invalid, and errors.
    """
    # Create the SQLAlchemy engine from the database URL.
    engine = create_engine_from_url(config.database_url)
    # Create the TMDB client.
    client = TmdbClient(config)
    # Calculate the delay seconds.
    delay_seconds = 1.0 / config.tmdb_rate_limit_rps if config.tmdb_rate_limit_rps > 0 else 0.0

    # Initialize the counts.
    fetched = 0
    skipped_invalid = 0
    errors = 0
    processed = 0
    after_movie_id = 0

    # Fetch the rows needing TMDB enrichment.
    while True:
        rows = fetch_rows_needing_tmdb_enrichment(
            engine,
            batch_size=config.enrich_batch_size,
            after_movie_id=after_movie_id,
        )
        # If there are no rows, break the loop.
        if not rows:
            break

        # For each row, fetch the TMDB metadata and update the catalog movie.
        for row in rows:
            # Get the movie ID and TMDB ID.
            movie_id = int(row["movie_id"])
            tmdb_id = int(row["tmdb_id"])
            after_movie_id = movie_id
            processed += 1

            # If the TMDB ID is not valid, skip the row.
            if tmdb_id <= 0:
                skipped_invalid += 1
                continue

            # Try to fetch the TMDB metadata.
            try:
                # Fetch the TMDB metadata.
                metadata = client.fetch_movie(tmdb_id)
                # If the TMDB metadata is not found, skip the row.
                if metadata is None:
                    skipped_invalid += 1
                    continue

                # Update the catalog movie with the TMDB metadata.
                update_catalog_tmdb_metadata(engine, movie_id, metadata)
                fetched += 1
            except Exception:
                # If an error occurs, log the error and increment the errors count.
                errors += 1
                logger.exception(
                    "Failed to fetch TMDB movie",
                    extra={"movie_id": movie_id, "tmdb_id": tmdb_id},
                )

            # If a delay is configured, sleep for the delay seconds.
            if delay_seconds > 0:
                time.sleep(delay_seconds)

            # If the number of fetched rows has been reached, log the progress.
            if fetched > 0 and fetched % config.log_every_n_rows == 0:
                logger.info(
                    "TMDB enrichment progress",
                    extra={
                        "fetched": fetched,
                        "processed": processed,
                        "errors": errors,
                    },
                )

    return {
        "processed": processed,
        "fetched": fetched,
        "skipped_invalid": skipped_invalid,
        "errors": errors,
    }


def main() -> None:
    """
    Run the TMDB enrichment job.

    ============================ Returns ============================
    None
    """
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    config = TmdbConfig.from_env()

    logger.info(
        "Starting TMDB enrichment",
        extra={
            "database_url": config.database_url.split("@")[-1],
            "rate_limit_rps": config.tmdb_rate_limit_rps,
            "enrich_batch_size": config.enrich_batch_size,
        },
    )

    summary = enrich_tmdb(config, logger)
    logger.info("TMDB enrichment completed", extra=summary)

    if summary["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "TMDB enrichment failed"
        )
        sys.exit(1)

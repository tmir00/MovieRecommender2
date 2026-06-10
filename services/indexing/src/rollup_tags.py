"""Roll up top user tags from tag_events into catalog_movies."""

from __future__ import annotations

import logging
import os
import sys

from config import IndexingConfig
from shared.db.engine import create_engine_from_url
from shared.db.tags import (
    aggregate_top_tags_by_movie,
    apply_tag_rollup_to_catalog,
    count_tag_events,
)
from shared.logging_config import configure_logging

def rollup_tags(config: IndexingConfig, logger: logging.Logger) -> dict[str, int]:
    """
    Aggregate tag_events and write top tags onto catalog_movies.

    Do this by:
    1. Checking that tag_events has rows (exit early if empty).
    2. Aggregating the top N tags per movie.
    3. Updating catalog_movies.tags and marking pending when tags change.

    ============================ Arguments ============================
    config: Indexing configuration with rollup batch size and top N.
    logger: Logger for progress output.

    ============================ Returns ============================
    Summary counts from aggregation and catalog update.
    """
    # Create the database engine to access the Postgres database.
    engine = create_engine_from_url(config.database_url)

    # Count the number of tag events in the tag_events table.
    tag_event_count = count_tag_events(engine)

    # If there are no tag events, skip the rollup.
    if tag_event_count == 0:
        logger.info(
            "No tag events found; skipping rollup",
            extra={"tag_events": 0},
        )
        return {
            "tag_events": 0,
            "movies_in_rollup": 0,
            "movies_updated": 0,
            "movies_marked_pending": 0,
            "movies_skipped_not_in_catalog": 0,
        }

    logger.info(
        "Aggregating top tags from tag_events",
        extra={
            "tag_events": tag_event_count,
            "tag_rollup_top_n": config.tag_rollup_top_n,
        },
    )

    # Aggregate the top tags from tag_events.
    rollup_rows = aggregate_top_tags_by_movie(
        engine,
        top_n=config.tag_rollup_top_n,
    )

    logger.info(
        "Applying tag rollup to catalog_movies",
        extra={
            "movies_in_rollup": len(rollup_rows),
            "tag_rollup_batch_size": config.tag_rollup_batch_size,
        },
    )

    # Apply the tag rollup to the catalog_movies table.
    update_counts = apply_tag_rollup_to_catalog(
        engine,
        rollup_rows,
        batch_size=config.tag_rollup_batch_size,
    )

    # Return the summary counts from aggregation and catalog update.
    return {
        "tag_events": tag_event_count,
        **update_counts,
    }


def main() -> None:
    """
    Run the tag rollup job.

    ============================ Returns ============================
    None
    """
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    # Configure the logging and load the configuration.
    config = IndexingConfig.from_env()

    logger.info(
        "Starting tag rollup",
        extra={
            "tag_rollup_top_n": config.tag_rollup_top_n,
            "tag_rollup_batch_size": config.tag_rollup_batch_size,
        },
    )

    # Run the tag rollup.
    summary = rollup_tags(config, logger)
    logger.info("Tag rollup completed", extra=summary)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "Tag rollup failed"
        )
        sys.exit(1)

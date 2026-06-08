"""Sync pending catalog_movies rows from Postgres to OpenSearch."""

from __future__ import annotations

import os
import sys
import logging

from config import IndexingConfig
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from opensearch_client import get_opensearch_client
from shared.logging_config import configure_logging
from shared.db.engine import create_engine_from_url
from shared.movie_document import build_movie_document
from shared.db.catalog import (
    fetch_pending_catalog_movies,
    mark_catalog_movies_synced,
)


def _ensure_alias_ready(client: OpenSearch, config: IndexingConfig) -> None:
    """
    Check if the movies alias exists in the OpenSearch cluster.
    If it doesn't, raise an error and ask the user to run the indexer pipeline first.
    """
    if not client.indices.exists_alias(name=config.movies_alias):
        raise RuntimeError(
            f"Movies alias '{config.movies_alias}' not found. Run index-catalog first."
        )


def sync_catalog(config: IndexingConfig, logger: logging.Logger) -> int:
    """
    Syncronize the pending catalog rows from the database to the OpenSearch cluster.

    Do this by:
    - Fetching the pending catalog rows from the database in batches.
    - Building the movie documents from the rows.
    - Sending the movie documents to the OpenSearch cluster in batches.

    ============================ Arguments ============================
    config: The configuration for the indexing run.
    logger: The logger to use.

    ============================ Returns ============================
    int - The total number of movies synced to the OpenSearch cluster.
    """
    # Get the OpenSearch client and ensure the movies alias exists.
    client = get_opensearch_client(config)
    _ensure_alias_ready(client, config)

    # Create the database engine to access the Postgres database.
    engine = create_engine_from_url(config.database_url)

    # Initialize counters for the number of movies synced and the number of failures.
    total_synced = 0
    total_failures = 0
    # Loop until we have synced all the pending catalog rows.
    try:
        while True:
            # Fetch the pending catalog rows from the database in batches.
            rows = fetch_pending_catalog_movies(
                engine,
                batch_size=config.sync_batch_size,
            )

            # If there are no pending catalog rows, break the loop.
            if not rows:
                break

            # Initialize a list to store the actions to be sent to the OpenSearch cluster.
            actions = []
            # Initialize a list to store the movie IDs to be marked as synced.
            movie_ids = []
            # Iterate over each row in the batch.
            for row in rows:
                # Build the movie document from the row and add it to the actions list.
                movie_id = row["movie_id"]
                doc = build_movie_document(
                    movie_id=movie_id,
                    title=row["title"],
                    genres=row["genres"],
                    year=row["year"],
                    tags=row["tags"],
                    pipeline_version=row["pipeline_version"],
                )

                actions.append(
                    {
                        "_index": config.movies_alias,
                        "_id": str(movie_id),
                        "_source": doc,
                    }
                )

                movie_ids.append(movie_id)

            # Send the actions to the OpenSearch cluster in batches.
            # Use the Bulk API to send the actions to the OpenSearch cluster.
            success, errors = bulk(
                client,
                actions,
                raise_on_error=False,
                raise_on_exception=False,
            )

            # Count the number of failures.
            failure_count = len(errors) if errors else 0
            # If there were any failures, log an error.
            if failure_count:
                logger.error(
                    "Catalog sync batch had failures",
                    extra={"success": success, "failure_count": failure_count},
                )
                total_failures += failure_count
                break

            # Mark the movie IDs as synced in the database.
            mark_catalog_movies_synced(engine, movie_ids)

            # Increment the total number of movies synced.
            total_synced += len(movie_ids)
            # Log the progress.
            logger.info(
                "Synced catalog batch to OpenSearch",
                extra={
                    "batch_size": len(movie_ids),
                    "movies_alias": config.movies_alias,
                    "total_synced": total_synced,
                },
            )
    finally:
        # Dispose of the database engine.
        engine.dispose()

    # If there were any failures, raise an error.
    if total_failures:
        raise RuntimeError(f"Catalog sync failed with {total_failures} bulk errors")

    return total_synced


def main() -> None:
    """
    Run the catalog sync job by:

    1. Configure logging and load the configuration.
    2. Log the start of the catalog sync job.
    3. Sync the catalog to the OpenSearch cluster.
    4. Log the completion of the catalog sync job.

    ============================ Returns ============================
    None
    """
    # Configure logging and load the configuration.
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    config = IndexingConfig.from_env()

    # Log the start of the catalog sync job.
    logger.info(
        "Starting catalog sync to OpenSearch",
        extra={
            "movies_alias": config.movies_alias,
            "sync_batch_size": config.sync_batch_size,
        },
    )

    # Sync the catalog to the OpenSearch cluster.
    synced = sync_catalog(config, logger)
    # Log the completion of the catalog sync job.
    logger.info(
        "Catalog sync completed",
        extra={"total_synced": synced, "movies_alias": config.movies_alias},
    )


if __name__ == "__main__":
    # Try to run the main function and log any exceptions.
    try:
        main()
    except Exception:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "Catalog sync failed"
        )
        sys.exit(1)

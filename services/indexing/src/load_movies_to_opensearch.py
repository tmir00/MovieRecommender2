"""Bulk-load active catalog_movies rows into the physical OpenSearch index."""

from __future__ import annotations

import os
import sys
import logging

from typing import Dict, Any
from build_index_document import build_index_documents_batch
from config import IndexingConfig
from embedder_client import EmbedderClient
from bulk_helpers import flush_bulk_batch, successful_movie_ids
from opensearch_client import get_opensearch_client
from shared.db.catalog import (
    fetch_active_catalog_movies_batch,
    mark_catalog_movies_synced,
)
from shared.db.engine import create_engine_from_url
from shared.features.adapters.postgres import row_to_catalog_input
from shared.features.models import CatalogMovieInput, TmdbMetadata
from shared.logging_config import configure_logging
from shared.tmdb.models import tmdb_metadata_from_catalog_row


def _rows_to_bulk_actions(config: IndexingConfig, embedder: EmbedderClient, rows: list[dict]) -> list[Dict[str, Any]]:
    """
    Transform catalog_movies rows into bulk actions with embedding-enriched documents.
    This is used by the load_movies function to build the batch of actions to be sent 
    to the OpenSearch cluster for bulk indexing.

    ============================ Arguments ============================
    config: The configuration for the indexing run.
    embedder: Client for the embedder HTTP API.
    rows: catalog_movies row dicts from Postgres.

    ============================= Returns =============================
    Bulk API action dicts for OpenSearch.
    """
    # Initialize an empty list to store the batch rows for .
    batch_rows = []
    # For each row, convert it to a catalog input and TMDB metadata.
    for row in rows:
        # Convert the row to a catalog input.
        catalog_input = row_to_catalog_input(row)

        # Get the TMDB metadata from the catalog row.
        tmdb = tmdb_metadata_from_catalog_row(row)

        # Add the catalog input and TMDB metadata to the batch rows to be indexed.
        batch_rows.append((catalog_input, tmdb))

    # Build the index documents for the batch rows.
    docs = build_index_documents_batch(embedder, config, batch_rows)

    # Build the bulk actions for the index documents.
    return [
        {
            "_index": config.physical_index,
            "_id": str(doc["movie_id"]),
            "_source": doc,
        }
        for doc in docs
    ]


def load_movies(config: IndexingConfig, logger: logging.Logger, embedder: EmbedderClient) -> tuple[int, int]:
    """
    Read catalog_movies in batches and bulk index into OpenSearch.

    Each row is converted into a movie document with an embedding vector and
    written to the physical index for this run, such as "movies_v4". The
    function batches documents for efficient bulk indexing, logs progress as it
    runs, and marks successfully indexed rows as synced in Postgres per batch.

    ============================ Arguments ============================
    config: The configuration for the indexing run.
    logger: The logger to use.
    embedder: Client for the embedder HTTP API.

    ============================ Returns ============================
    tuple[int, int] - The number of rows read and the number of failures.
    """
    # Get the OpenSearch client and the database engine.
    client = get_opensearch_client(config)
    engine = create_engine_from_url(config.database_url)

    # Initialize the counters.
    rows_read = 0
    rows_indexed = 0
    total_failures = 0
    after_movie_id = 0

    # Loop until we have read all the active catalog movies.
    while True:
        # If the maximum number of movies has been reached, break the loop.
        if config.max_movies > 0 and rows_read >= config.max_movies:
            break

        # Calculate the batch size.
        batch_size = config.bulk_chunk_size
        
        # If the maximum number of movies has been reached, use the maximum number of movies.
        if config.max_movies > 0:
            batch_size = min(batch_size, config.max_movies - rows_read)

        # Fetch the active catalog movies in batches.
        rows = fetch_active_catalog_movies_batch(
            engine,
            batch_size=batch_size,
            after_movie_id=after_movie_id,
        )
        # If there are no rows, break the loop.
        if not rows:
            break

        # Get the movie IDs from the rows.
        batch_movie_ids = [int(row["movie_id"]) for row in rows]

        # Build the bulk actions for the rows.
        actions = _rows_to_bulk_actions(config, embedder, rows)

        # Send the bulk actions to the OpenSearch cluster.
        failures, failed_ids = flush_bulk_batch(
            client,
            actions,
            logger,
            log_context="Bootstrap bulk load",
        )

        # Update the counters.
        rows_read += len(rows)
        rows_indexed += len(actions) - failures

        # Update the total number of failures.
        total_failures += failures

        # Get the successful movie IDs.
        success_ids = successful_movie_ids(batch_movie_ids, failed_ids)
        # If there are any successful movie IDs, mark the catalog movies as synced.
        if success_ids:
            mark_catalog_movies_synced(engine, success_ids)

        after_movie_id = int(rows[-1]["movie_id"])

        # If the number of rows indexed has been reached, log the progress.
        if rows_indexed > 0 and rows_indexed % config.log_every_n_docs == 0:
            logger.info(
                "Indexed movie documents",
                extra={
                    "rows_indexed": rows_indexed,
                    "physical_index": config.physical_index,
                },
            )

    # Log the completion of the bulk load.
    logger.info(
        "Finished bulk load",
        extra={
            "rows_read": rows_read,
            "rows_indexed": rows_indexed,
            "bulk_failures": total_failures,
            "physical_index": config.physical_index,
        },
    )
    return rows_read, total_failures


def main() -> None:
    """
    Run the movie bulk indexing job.

    This is the entry point for loading movie documents into OpenSearch. It
    loads environment-based config, initializes logging, bulk indexes movies
    from catalog_movies in Postgres, and exits with a non-zero status code if any
    documents fail to index.

    A non-zero exit code is useful for Docker, CI/CD, or future Kubernetes Jobs
    because the indexing run can be marked as failed.
    """
    # Configure logging and load the configuration.
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    config = IndexingConfig.from_env()
    embedder = EmbedderClient(config.embedder_url)
    logger.info("Starting movie bulk load", extra=config.startup_log_extra())

    # Bulk load the movies into OpenSearch.
    _, failures = load_movies(config, logger, embedder)

    # If there were any failures, log a critical error and exit with a non-zero status code.
    if failures:
        logger.critical(
            "Bulk load completed with failures",
            extra={"bulk_failures": failures},
        )
        sys.exit(1)


if __name__ == "__main__":
    # Try to run the main function and log any exceptions.
    try:
        main()
    except Exception:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "Failed to bulk load movies"
        )
        sys.exit(1)

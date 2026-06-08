"""Bulk-load movies.csv into the physical OpenSearch index."""

from __future__ import annotations

import os
import sys
import logging
import pandas as pd

from typing import Dict, Any
from build_index_document import build_index_documents_batch
from config import IndexingConfig
from embedder_client import EmbedderClient
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from transform import row_to_index_fields
from opensearch_client import get_opensearch_client
from shared.logging_config import configure_logging


def _rows_to_bulk_actions(config: IndexingConfig, embedder: EmbedderClient, \
                            rows: list[object]) -> list[Dict[str, Any]]:
    """
    Transform CSV rows into bulk actions with embedding-enriched documents.

    ============================ Arguments ============================
    config: The configuration for the indexing run.
    embedder: Client for the embedder HTTP API.
    rows: movies.csv row objects from one chunk.

    ============================ Returns ============================
    Bulk API action dicts for OpenSearch.
    """
    fields = [row_to_index_fields(row) for row in rows]
    docs = build_index_documents_batch(embedder, config, fields)
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
    Read movies.csv in chunks and bulk index the movies into OpenSearch.

    Each row is converted into a movie document with an embedding vector and
    written to the physical index for this run, such as "movies_v2". The
    function batches documents for efficient bulk indexing, logs progress as it
    runs, and returns a summary of how many rows were processed and how many
    indexing failures occurred.

    ============================ Arguments ============================
    config: The configuration for the indexing run.
    logger: The logger to use.
    embedder: Client for the embedder HTTP API.

    ============================ Returns ============================
    tuple[int, int] - The number of rows read and the number of failures.
    """
    # Get the OpenSearch client.
    client = get_opensearch_client(config)
    # Initialize counters for the number of rows read and indexed, and the number of failures.
    rows_read = 0
    rows_indexed = 0
    total_failures = 0

    # Initialize a list to store the documents to be indexed.
    batch: list[dict] = []
    row_buffer: list[object] = []

    # Read the movies.csv file in chunks of size bulk_chunk_size.
    for chunk in pd.read_csv(config.movies_csv_path, chunksize=config.bulk_chunk_size):

        # Iterate over each row in the chunk.
        for row in chunk.itertuples(index=False):

            # If we have reached the maximum number of movies to index, break.
            if config.max_movies > 0 and rows_read >= config.max_movies:
                break

            # Increment the number of rows read.
            rows_read += 1
            row_buffer.append(row)

            # If the batch is full, build embeddings and flush to OpenSearch.
            if len(row_buffer) >= config.bulk_chunk_size:
                batch = _rows_to_bulk_actions(config, embedder, row_buffer)
                failures = _flush_batch(client, batch, logger)
                rows_indexed += len(batch) - failures
                total_failures += failures
                row_buffer.clear()
                batch.clear()

                # If we have reached the log_every_n_docs threshold, log the progress.
                if rows_indexed % config.log_every_n_docs == 0:
                    logger.info(
                        "Indexed movie documents",
                        extra={
                            "rows_indexed": rows_indexed,
                            "physical_index": config.physical_index,
                        },
                    )

        # If we have reached the maximum number of movies to index, break.
        if config.max_movies > 0 and rows_read >= config.max_movies:
            break

    # If there are any rows left in the buffer, build embeddings and flush them.
    if row_buffer:
        batch = _rows_to_bulk_actions(config, embedder, row_buffer)
        failures = _flush_batch(client, batch, logger)
        rows_indexed += len(batch) - failures
        total_failures += failures

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


def _flush_batch(client: OpenSearch, batch: list[dict], logger: logging.Logger) -> int:
    """
    Send one batch of movie documents to OpenSearch using the Bulk API.

    The batch list contains dictionaries in the exact format that the Bulk API expects.
    This function writes them to the target index, counts any failed items, and logs an
    error if the batch was only partially successful.

    ============================ Arguments ============================
    client: The OpenSearch client.
    batch: The list of movie documents to send.
    logger: The logger to use.

    ============================ Returns ============================
    int - The number of failed items.
    """
    # Send the batch to the OpenSearch index using the Bulk API.
    success, errors = bulk(
        client,
        batch,
        raise_on_error=False,
        raise_on_exception=False,
    )

    # Count the number of failed items.
    failure_count = len(errors) if errors else 0
    # If there were any failures, log an error.
    if failure_count:
        logger.error(
            "Bulk batch had failures",
            extra={"success": success, "failure_count": failure_count},
        )

    return failure_count


def main() -> None:
    """
    Run the movie bulk indexing job.

    This is the entry point for loading movie documents into OpenSearch. It
    loads environment-based config, initializes logging, bulk indexes movies
    from the configured CSV file, and exits with a non-zero status code if any
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

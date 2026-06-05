"""Bulk-load movies.csv into the physical OpenSearch index."""

from __future__ import annotations

import os
import sys
import logging
import pandas as pd

from typing import Dict, Any
from config import IndexingConfig
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from transform import row_to_document
from opensearch_client import get_opensearch_client
from shared.logging_config import configure_logging


def _bulk_actions(config: IndexingConfig, row: object) -> Dict[str, Any]:
    """
    Transform one movies.csv row into an OpenSearch document body.

    ============================ Arguments ============================
    config: The configuration for the indexing run.
    row: The row to transform.

    ============================ Returns ============================
    dict - The OpenSearch document body.
    """
    # Transform the row into an OpenSearch document body.
    doc = row_to_document(row, config.pipeline_version)
    # Return the OpenSearch document body.
    return {
        # The index to store the document in.
        "_index": config.physical_index,
        # The document ID.
        "_id": str(doc["movie_id"]),
        # The document body.
        "_source": doc,
    }


def load_movies(config: IndexingConfig, logger: logging.Logger) -> tuple[int, int]:
    """
    Read movies.csv in chunks and bulk index the movies into OpenSearch.

    Each row is converted into a movie document and written to the physical
    index for this run, such as "movies_v1". The function batches documents for
    efficient bulk indexing, logs progress as it runs, and returns a summary of
    how many rows were processed and how many indexing failures occurred.

    ============================ Arguments ============================
    config: The configuration for the indexing run.
    logger: The logger to use.

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

    # Read the movies.csv file in chunks of size bulk_chunk_size.
    for chunk in pd.read_csv(config.movies_csv_path, chunksize=config.bulk_chunk_size):
        
        # Iterate over each row in the chunk.
        for row in chunk.itertuples(index=False):
        
            # If we have reached the maximum number of movies to index, break.
            if config.max_movies > 0 and rows_read >= config.max_movies:
                break

            # Increment the number of rows read.
            rows_read += 1
            # Add the document to the batch.
            batch.append(_bulk_actions(config, row))

            # If the batch is full, flush it to the OpenSearch index.
            if len(batch) >= config.bulk_chunk_size:
                # Flush the batch to the OpenSearch index and increment counters.
                failures = _flush_batch(client, batch, logger)
                rows_indexed += len(batch) - failures
                total_failures += failures
                # Empty the batch list after everything has been flushed.
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


    # If there are any documents left in the batch, flush them to the OpenSearch index.
    if batch:
        # Flush the batch to the OpenSearch index and increment counters.
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
    logger.info("Starting movie bulk load", extra=config.startup_log_extra())

    # Bulk load the movies into OpenSearch.
    _, failures = load_movies(config, logger)

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

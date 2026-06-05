"""Orchestrate catalog indexing: create index, bulk load, promote alias, smoke test."""

from __future__ import annotations

import os
import sys
import logging

from alias import promote_alias
from config import IndexingConfig
from create_movies_index import create_movies_index
from load_movies_to_opensearch import load_movies
from smoke_test_movies_index import run_smoke_tests
from shared.logging_config import configure_logging
from opensearch_client import get_opensearch_client

def run_pipeline(config: IndexingConfig, logger: logging.Logger) -> None:
    """
    Run the full catalog indexing pipeline.

    This function orchestrates the entire movie catalog indexing process, including:
    - Creating the versioned OpenSearch index
    - Bulk loading movie documents into the index
    - Promoting the alias to the new index
    - Running smoke tests to verify the index is working
    """
    # Log the start of the indexing pipeline.
    logger.info("Starting catalog indexing pipeline", extra=config.startup_log_extra())

    # Create the versioned OpenSearch index.
    create_movies_index(config, logger)

    # Bulk load the movie documents into the index.
    _, failures = load_movies(config, logger)
    if failures:
        raise RuntimeError(f"Bulk load had {failures} failures")

    # Promote the alias to the new index.
    promote_alias(get_opensearch_client(config), config, logger)

    # Run the smoke tests to verify the index is working.
    run_smoke_tests(config, logger)

    logger.info(
        "Catalog indexing pipeline completed",
        extra={
            "physical_index": config.physical_index,
            "movies_alias": config.movies_alias,
        },
    )


def main() -> None:
    """
    Run the catalog indexing pipeline. 
    This function loads environment-based config, initializes logging, and runs the catalog indexing pipeline.
    It also logs any exceptions that occur during the pipeline.
    """
    # Configure logging and load the configuration.
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    config = IndexingConfig.from_env()
    
    # Run the catalog indexing pipeline.
    try:
        run_pipeline(config, logger)
    except Exception:
        logger.exception("Catalog indexing pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

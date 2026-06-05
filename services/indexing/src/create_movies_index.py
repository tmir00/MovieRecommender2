"""Create the versioned physical movies index in OpenSearch."""

from __future__ import annotations

import os
import sys
import logging

from config import IndexingConfig
from movie_mapping import MOVIES_INDEX_MAPPING
from opensearch_client import get_opensearch_client
from shared.logging_config import configure_logging


def create_movies_index(config: IndexingConfig, logger: logging.Logger) -> None:
    """
    Create the versioned OpenSearch index that will store movie documents.

    The app reads from a stable alias like "movies", but this indexing run writes
    to a real physical index like "movies_v1" or "movies_v2". This function
    creates that physical index using the movie mapping.

    If the physical index already exists:
    - return without changing it when recreate_index is False
    - delete and rebuild it when recreate_index is True

    recreate_index=True is useful for local development, but should be used
    carefully because it deletes the existing physical index.

    ============================ Arguments ============================
    config: IndexingConfig - The configuration for the indexing run.
    logger: logging.Logger - The logger to use.

    ============================ Returns ============================
    None
    """
    # Get the OpenSearch client and the physical index name to create (e.g: "movies_v1").
    client = get_opensearch_client(config)
    index_name = config.physical_index

    # If the physical index already exists, check if we should recreate it.
    if client.indices.exists(index=index_name):
        # If we shouldn't recreate it, log a message and return.
        if not config.recreate_index:
            logger.info(
                "Physical index already exists",
                extra={"physical_index": index_name},
            )
            return

        # If we should recreate it, delete the existing physical index.
        logger.warning(
            "Deleting existing physical index for recreate",
            extra={"physical_index": index_name},
        )
        client.indices.delete(index=index_name)

    # Create the physical index with the movie mapping.
    client.indices.create(index=index_name, body=MOVIES_INDEX_MAPPING)
    logger.info(
        "Created physical index",
        extra={"physical_index": index_name},
    )


def main() -> None:
    """
    Start the movie indexer setup job.

    Loads environment-based config, initializes logging, and creates the
    versioned OpenSearch movie index for this run. This prepares the index
    before movie documents are bulk loaded.

    ============================ Returns ============================
    None
    """
    # Configure logging and load the configuration.
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    config = IndexingConfig.from_env()
    logger.info("Creating movies index", extra=config.startup_log_extra())
    create_movies_index(config, logger)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "Failed to create movies index"
        )
        sys.exit(1)

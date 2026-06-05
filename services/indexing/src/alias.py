"""Index alias management for zero-downtime catalog cutover."""

from __future__ import annotations

import logging

from config import IndexingConfig
from opensearchpy import OpenSearch


def promote_alias(client: OpenSearch, config: IndexingConfig, logger: logging.Logger) -> None:
    """
    Make this newly built movie index the one the app reads from.

    The app queries a stable alias, such as "movies", instead of querying a
    versioned index directly, such as "movies_v1" or "movies_v2". This function
    moves that alias from the old index to the new physical index created by
    this indexing run.

    After this runs:
        movies -> movies_v2

    instead of:
        movies -> movies_v1

    This is called "zero-downtime catalog cutover" because the app can continue 
    to read from the old index while the new one is being built.


    ============================ Arguments ============================
    client: OpenSearch - The OpenSearch client to use.
    config: IndexingConfig - The configuration for the indexing run.
    logger: logging.Logger - The logger to use.

    ============================ Returns ============================
    None
    """
    # Fetcg the current alias and physical index names.
    # This is the alias that the app reads from (e.g. movies).
    alias = config.movies_alias
    # This is the real versioned index name (e.g. movies_v2).
    physical = config.physical_index

    # If the alias already exists (e.g: "movies" -> "movies_v1"), remove it from the old index.
    if client.indices.exists_alias(name=alias):
        # Get the list of old indices that the alias is pointing to.
        existing = client.indices.get_alias(name=alias)

        # For each old index, remove the alias from it.
        for old_index in existing:
            logger.info(
                "Removing alias from previous index",
                extra={"alias": alias, "old_index": old_index},
            )
            client.indices.delete_alias(index=old_index, name=alias)

    # Add the alias to the new physical index.
    client.indices.put_alias(index=physical, name=alias)
    logger.info(
        "Promoted alias to physical index",
        extra={"alias": alias, "physical_index": physical},
    )

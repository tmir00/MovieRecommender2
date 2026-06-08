"""Health helpers for the catalog indexer API."""

from __future__ import annotations

from config import IndexingConfig
from opensearchpy import OpenSearch


def opensearch_ready(client: OpenSearch, config: IndexingConfig) -> bool:
    """
    ! Health check function.

    Check whether OpenSearch is reachable and the movie search index is ready.

    The function first verifies that the OpenSearch cluster responds to a ping.
    It then checks whether the configured movies alias exists. This is useful
    for health checks because the API should only be considered ready when it
    can connect to OpenSearch and query the expected movie index alias.

    ============================ Arguments ============================
    client: The OpenSearch client used to check cluster availability.
    config: Indexing configuration containing the movies index alias.

    ============================= Returns =============================
    True if OpenSearch is reachable and the movies alias exists; otherwise False.
    """
    try:
        if not client.ping():
            return False
        return client.indices.exists_alias(name=config.movies_alias)
    except Exception:
        return False

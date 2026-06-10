"""OpenSearch client factory."""

from __future__ import annotations

from config import IndexingConfig
from opensearchpy import OpenSearch


def get_opensearch_client(config: IndexingConfig) -> OpenSearch:
    """
    Build the OpenSearch connection used by the indexer.

    The indexer uses this client to create indices, promote aliases, and bulk
    load movie documents. Host and port come from environment-based config, so
    the same code can connect to localhost in local runs or to the "opensearch"
    Docker service inside Compose.

    ============================ Arguments ============================
    config: The configuration for the indexing run.

    ============================ Returns ============================
    OpenSearch - The OpenSearch client.
    """
    return OpenSearch(
        hosts=[{"host": config.opensearch_host, "port": config.opensearch_port}],
        use_ssl=False,
        verify_certs=False,
        # Whether to compress the HTTP requests.
        http_compress=True,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )

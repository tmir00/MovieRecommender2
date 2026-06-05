"""
Here we create the OpenSearch client that will be used to interact with the OpenSearch cluster.
This is used by the recommender API to read from and write to the OpenSearch cluster..
"""

from __future__ import annotations

from opensearchpy import OpenSearch

from config import RecommenderApiConfig


def get_opensearch_client(config: RecommenderApiConfig) -> OpenSearch:
    """
    Build the OpenSearch connection used by the recommender API.

    ============================ Arguments ============================
    config: RecommenderApiConfig - The configuration for the recommender API.

    ============================ Returns ============================
    OpenSearch - The OpenSearch client.
    """
    return OpenSearch(
        hosts=[{"host": config.opensearch_host, "port": config.opensearch_port}],
        use_ssl=False,
        verify_certs=False,
        http_compress=True,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )

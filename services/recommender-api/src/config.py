"""Recommender API configuration."""

from __future__ import annotations

import os

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommenderApiConfig:
    """
    Runtime settings for the recommender API.
    """
    database_url: str
    opensearch_host: str
    opensearch_port: int
    movies_alias: str
    api_host: str
    api_port: int
    pipeline_version: str
    catalog_indexer_url: str
    embedder_url: str
    embedding_dimension: int

    @classmethod
    def from_env(cls) -> RecommenderApiConfig:
        return cls(
            database_url=os.environ["DATABASE_URL"],
            opensearch_host=os.environ.get("OPENSEARCH_HOST", "opensearch"),
            opensearch_port=int(os.environ.get("OPENSEARCH_PORT", "9200")),
            movies_alias=os.environ.get("OPENSEARCH_INDEX_MOVIES", "movies"),
            api_host=os.environ.get("RECOMMENDER_API_HOST", "0.0.0.0"),
            api_port=int(os.environ.get("RECOMMENDER_API_PORT", "8000")),
            pipeline_version=os.environ.get("PIPELINE_VERSION", "v1"),
            catalog_indexer_url=os.environ.get(
                "CATALOG_INDEXER_URL", "http://catalog-indexer-api:8101"
            ),
            embedder_url=os.environ.get("EMBEDDER_URL", "http://embedder:8100"),
            embedding_dimension=int(os.environ.get("EMBEDDING_DIMENSION", "384")),
        )

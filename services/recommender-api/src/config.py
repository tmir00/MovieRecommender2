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
    # OpenSearch Vector Search Config.
    similar_min_vote_count: int # Minimum TMDB vote count before we consider the movie.
    similar_knn_candidates: int # Maximum number of neighbors to return.
    similar_popularity_factor: float # Popularity factor for boosting the score.
    similar_vote_average_factor: float # Vote average factor for boosting the score.

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
            similar_min_vote_count=int(os.environ.get("SIMILAR_MIN_VOTE_COUNT", "50")),
            similar_knn_candidates=int(os.environ.get("SIMILAR_KNN_CANDIDATES", "50")),
            similar_popularity_factor=float(
                os.environ.get("SIMILAR_POPULARITY_FACTOR", "0.05")
            ),
            similar_vote_average_factor=float(
                os.environ.get("SIMILAR_VOTE_AVERAGE_FACTOR", "0.1")
            ),
        )

"""Indexing configuration loaded from environment variables."""

from __future__ import annotations

import os
from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True)
class IndexingConfig:
    """Runtime settings for the movie catalog indexing job."""

    # OpenSearch Connection Details
    opensearch_host: str
    opensearch_port: int

    # Movies Index Versioning Details
    movies_alias: str
    index_version: str

    # Movies CSV Path
    movies_csv_path: str
    # The size of the bulk chunk to index at a time.
    bulk_chunk_size: int
    # Whether to recreate the index.
    recreate_index: bool
    # This is stored on each movie document to track the version of the pipeline that indexed it.
    pipeline_version: str
    # How often the bulk loader prints progress.
    log_every_n_docs: int
    # The maximum number of movies to index for debugging.
    max_movies: int
    database_url: str
    sync_batch_size: int
    catalog_indexer_host: str
    catalog_indexer_port: int
    # Configuration for the embedder service.
    embedder_url: str
    embedding_model_id: str
    embedding_dimension: int
    embed_batch_size: int
    # CSV paths used by seed-catalog only.
    links_csv_path: str
    # Tag rollup job settings (rollup-tags).
    tag_rollup_top_n: int
    tag_rollup_batch_size: int

    @property
    def physical_index(self) -> str:
        """ Return the versioned physical index name (e.g. movies_v1). """
        return f"movies_{self.index_version}"

    @classmethod
    def from_env(cls) -> IndexingConfig:
        """ Load settings from the environment. """
        return cls(
            opensearch_host=os.environ.get("OPENSEARCH_HOST", "opensearch"),
            opensearch_port=int(os.environ.get("OPENSEARCH_PORT", "9200")),
            movies_alias=os.environ.get("OPENSEARCH_INDEX_MOVIES", "movies"),
            index_version=os.environ.get("INDEX_VERSION", "v1"),
            movies_csv_path=os.environ.get(
                "MOVIES_CSV_PATH", "/data/ml-25m/movies.csv"
            ),
            bulk_chunk_size=int(os.environ.get("OPENSEARCH_BULK_CHUNK_SIZE", "1000")),
            recreate_index=os.environ.get("RECREATE_INDEX", "false").lower() in ("1", "true", "yes"),
            pipeline_version=os.environ.get("PIPELINE_VERSION", "v1"),
            log_every_n_docs=int(os.environ.get("LOG_EVERY_N_DOCS", "5000")),
            max_movies=int(os.environ.get("MAX_MOVIES", "0")),
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgresql+psycopg://movierec:movierec@postgres:5432/movierec",
            ),
            sync_batch_size=int(os.environ.get("SYNC_BATCH_SIZE", "500")),
            catalog_indexer_host=os.environ.get("CATALOG_INDEXER_HOST", "0.0.0.0"),
            catalog_indexer_port=int(os.environ.get("CATALOG_INDEXER_PORT", "8101")),
            embedder_url=os.environ.get("EMBEDDER_URL", "http://embedder:8100"),
            embedding_model_id=os.environ.get(
                "EMBEDDING_MODEL_ID",
                "sentence-transformers/all-MiniLM-L6-v2",
            ),
            embedding_dimension=int(os.environ.get("EMBEDDING_DIMENSION", "384")),
            embed_batch_size=int(os.environ.get("EMBED_BATCH_SIZE", "32")),
            links_csv_path=os.environ.get(
                "LINKS_CSV_PATH",
                "/data/ml-25m/links.csv",
            ),
            tag_rollup_top_n=int(os.environ.get("TAG_ROLLUP_TOP_N", "15")),
            tag_rollup_batch_size=int(os.environ.get("TAG_ROLLUP_BATCH_SIZE", "500")),
        )

    def startup_log_extra(self) -> dict[str, Any]:
        """ Structured fields for pipeline startup logs. """
        return {
            "opensearch_host": self.opensearch_host,
            "opensearch_port": self.opensearch_port,
            "movies_alias": self.movies_alias,
            "physical_index": self.physical_index,
            "movies_csv_path": self.movies_csv_path,
            "bulk_chunk_size": self.bulk_chunk_size,
            "recreate_index": self.recreate_index,
            "pipeline_version": self.pipeline_version,
            "max_movies": self.max_movies,
        }

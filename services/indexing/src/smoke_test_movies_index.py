"""Post-index smoke tests for the movie catalog."""

from __future__ import annotations

import os
import sys
import logging

from opensearchpy import OpenSearch

from config import IndexingConfig
from opensearch_client import get_opensearch_client
from shared.db.catalog import count_active_catalog_movies
from shared.db.engine import create_engine_from_url
from shared.features.constants import LEXICAL_SEARCH_FIELDS
from shared.features.similar_search import (
    DEFAULT_SIMILAR_POPULARITY_FACTOR,
    DEFAULT_SIMILAR_VOTE_AVERAGE_FACTOR,
    build_similar_search_query,
)
from shared.logging_config import configure_logging


def _expected_row_count(config: IndexingConfig) -> int:
    if config.max_movies > 0:
        return config.max_movies
    engine = create_engine_from_url(config.database_url)
    return count_active_catalog_movies(engine)


def _read_index_name(config: IndexingConfig, client: OpenSearch) -> str:
    """Prefer alias for reads when it exists."""
    if client.indices.exists_alias(name=config.movies_alias):
        return config.movies_alias
    return config.physical_index


def run_smoke_tests(config: IndexingConfig, logger: logging.Logger) -> None:
    """Run validation queries; raise RuntimeError on failure."""
    client = get_opensearch_client(config)
    read_index = _read_index_name(config, client)

    if not client.indices.exists(index=config.physical_index):
        raise RuntimeError(f"Physical index missing: {config.physical_index}")

    expected = _expected_row_count(config)
    count_response = client.count(index=read_index)
    doc_count = count_response["count"]

    if doc_count < expected:
        raise RuntimeError(
            f"Document count too low: got {doc_count}, expected at least {expected}"
        )

    logger.info(
        "Document count check passed",
        extra={
            "read_index": read_index,
            "doc_count": doc_count,
            "expected_min": expected,
        },
    )

    search_response = client.search(
        index=read_index,
        body={
            "size": 5,
            "query": {
                "multi_match": {
                    "query": "toy story",
                    "fields": LEXICAL_SEARCH_FIELDS,
                }
            },
        },
    )
    hits = search_response["hits"]["hits"]
    if not hits:
        raise RuntimeError("Text search smoke test returned no hits for 'toy story'")

    top_title = hits[0]["_source"].get("title", "")
    if "Toy Story" not in top_title:
        raise RuntimeError(
            f"Expected Toy Story in top hit, got: {top_title!r}"
        )

    logger.info(
        "Text search smoke test passed",
        extra={"read_index": read_index, "top_title": top_title},
    )

    genre_response = client.search(
        index=read_index,
        body={
            "size": 1,
            "query": {"term": {"genres": "Animation"}},
        },
    )
    total = genre_response["hits"]["total"]
    hit_count = total["value"] if isinstance(total, dict) else total
    if hit_count == 0:
        raise RuntimeError("Genre filter smoke test returned no Animation hits")

    logger.info(
        "Genre filter smoke test passed",
        extra={"read_index": read_index, "genre": "Animation"},
    )

    sample_response = client.search(
        index=read_index,
        body={"size": 1, "query": {"match_all": {}}},
    )
    sample_hits = sample_response["hits"]["hits"]
    if not sample_hits:
        raise RuntimeError("Embedding smoke test could not sample a document")

    sample_source = sample_hits[0]["_source"]
    sample_tags = sample_source.get("tags") or []
    logger.info(
        "Sample document tags check",
        extra={
            "read_index": read_index,
            "has_tags": bool(sample_tags),
        },
    )

    embedding = sample_source.get("embedding")
    if not embedding:
        raise RuntimeError("Sample document is missing embedding field")
    if len(embedding) != config.embedding_dimension:
        raise RuntimeError(
            f"Embedding dimension mismatch: got {len(embedding)}, "
            f"expected {config.embedding_dimension}"
        )

    logger.info(
        "Embedding field smoke test passed",
        extra={
            "read_index": read_index,
            "embedding_dimension": len(embedding),
        },
    )

    knn_response = client.search(
        index=read_index,
        body={
            "size": 3,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": embedding,
                        "k": 3,
                    }
                }
            },
        },
    )
    if not knn_response["hits"]["hits"]:
        raise RuntimeError("kNN smoke test returned no hits")

    logger.info(
        "kNN vector search smoke test passed",
        extra={"read_index": read_index, "knn_hits": len(knn_response["hits"]["hits"])},
    )

    function_score_response = client.search(
        index=read_index,
        body={
            "size": 3,
            "query": build_similar_search_query(
                embedding,
                knn_k=50,
                popularity_factor=DEFAULT_SIMILAR_POPULARITY_FACTOR,
                vote_average_factor=DEFAULT_SIMILAR_VOTE_AVERAGE_FACTOR,
            ),
        },
    )
    if not function_score_response["hits"]["hits"]:
        raise RuntimeError("function_score kNN smoke test returned no hits")

    logger.info(
        "function_score kNN smoke test passed",
        extra={
            "read_index": read_index,
            "hits": len(function_score_response["hits"]["hits"]),
        },
    )

    sample_source = sample_hits[0]["_source"]
    if "search_text" in sample_source:
        raise RuntimeError("Sample document still contains deprecated search_text field")

    if sample_source.get("tmdb_id") is not None:
        if "popularity" not in sample_source:
            raise RuntimeError("Sample doc with tmdb_id is missing popularity field")
        if "vote_count" not in sample_source:
            raise RuntimeError("Sample doc with tmdb_id is missing vote_count field")
        if "overview" not in sample_source:
            raise RuntimeError("Sample doc with tmdb_id is missing overview field")
        logger.info(
            "TMDB lexical + scalar fields smoke test passed",
            extra={
                "read_index": read_index,
                "tmdb_id": sample_source.get("tmdb_id"),
                "has_tagline": "tagline" in sample_source,
            },
        )


def main() -> None:
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    config = IndexingConfig.from_env()
    logger.info(
        "Running smoke tests",
        extra={
            "physical_index": config.physical_index,
            "movies_alias": config.movies_alias,
        },
    )
    run_smoke_tests(config, logger)
    logger.info("All smoke tests passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "Smoke tests failed",
            extra={"error": str(exc)},
        )
        sys.exit(1)

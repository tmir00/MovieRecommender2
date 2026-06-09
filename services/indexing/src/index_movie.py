"""Index a single catalog movie into OpenSearch."""

from __future__ import annotations

import logging

from config import IndexingConfig
from opensearchpy import OpenSearch
from embedder_client import EmbedderClient
from build_index_document import build_index_document
from opensearchpy.exceptions import OpenSearchException
from shared.features.models import CatalogMovieInput, TmdbMetadata

logger = logging.getLogger(__name__)


def index_movie_document(client: OpenSearch, config: IndexingConfig, embedder: EmbedderClient, \
                            catalog_input: CatalogMovieInput, *, tmdb: TmdbMetadata | None = None, \
                            pipeline_version: str | None = None) -> tuple[bool, str | None]:
    """
    Upsert one movie document into the movies alias.

    Do this by:
    1. Checking if the movies alias exists.
    2. Building the movie document with an embedding vector and search text.
    3. Indexing the movie document into the movies alias.
    4. Returning the success and error message.

    ============================ Arguments ============================
    client: The OpenSearch client.
    config: The configuration for the indexing run.
    embedder: Client for the embedder HTTP API.
    catalog_input: Normalized catalog fields for one movie.
    tmdb: Optional TMDB metadata from the Postgres catalog row or a live fetch.
    pipeline_version: The pipeline version of the movie to index.

    ============================ Returns ============================
    The success and error message.
    """
    try:
        # Check if the movies alias exists.
        if not client.indices.exists_alias(name=config.movies_alias):
            # If the movies alias doesn't exist, return a failure and an error message.
            return (
                False,
                f"Movies alias '{config.movies_alias}' not found. Run index-catalog job first.",
            )

        # Build the movie document with lexical fields and an embedding vector.
        doc = build_index_document(
            embedder,
            config,
            catalog_input,
            tmdb=tmdb,
            pipeline_version=pipeline_version,
        )

        # Index the movie document into the movies alias.
        client.index(
            index=config.movies_alias,
            id=str(catalog_input.movie_id),
            body=doc,
            refresh=True,
        )
        return True, None

    # If an OpenSearch exception occurs, log the error and return a failure and an error message.
    except OpenSearchException as exc:
        logger.exception("Failed to index movie %s in OpenSearch", catalog_input.movie_id)
        return False, str(exc)

    # If an exception occurs, log the error and return a failure and an error message.
    except Exception as exc:
        logger.exception("Failed to index movie %s in OpenSearch", catalog_input.movie_id)
        return False, str(exc)

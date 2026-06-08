"""Index a single catalog movie into OpenSearch."""

from __future__ import annotations

import logging

from config import IndexingConfig
from opensearchpy import OpenSearch
from embedder_client import EmbedderClient
from build_index_document import build_index_document
from opensearchpy.exceptions import OpenSearchException


logger = logging.getLogger(__name__)


def index_movie_document(client: OpenSearch, config: IndexingConfig, embedder: EmbedderClient, *, \
                        movie_id: int, title: str, genres: list[str], year: int | None = None, \
                        tags: list[str] | None = None, pipeline_version: str | None = None) -> tuple[bool, str | None]:
    """
    Upsert one movie document into the movies alias.

    Do this by:
    1. Checking if the movies alias exists.
    2. Building the movie document with an embedding vector.
    3. Indexing the movie document into the movies alias.
    4. Returning the success and error message.

    ============================ Arguments ============================
    client: The OpenSearch client.
    config: The configuration for the indexing run.
    embedder: Client for the embedder HTTP API.
    movie_id: The ID of the movie to index.
    title: The title of the movie to index.
    genres: The genres of the movie to index.
    year: The year of the movie to index.
    tags: The tags of the movie to index.
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
            movie_id=movie_id,
            title=title,
            genres=genres,
            year=year,
            tags=tags or [],
        )
        if pipeline_version:
            doc["pipeline_version"] = pipeline_version

        # Index the movie document into the movies alias.
        client.index(
            index=config.movies_alias,
            id=str(movie_id),
            body=doc,
            refresh=True,
        )
        # Return a success and no error message.
        return True, None

    # If there was an OpenSearch exception, return a failure and the error message.
    except OpenSearchException as exc:
        logger.exception("Failed to index movie %s in OpenSearch", movie_id)
        return False, str(exc)

    # If there was an exception, return a failure and the error message.
    except Exception as exc:
        logger.exception("Failed to index movie %s in OpenSearch", movie_id)
        return False, str(exc)

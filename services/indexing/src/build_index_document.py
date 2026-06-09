"""Build full OpenSearch movie documents with lexical fields and embeddings."""

from __future__ import annotations

from typing import Any

from config import IndexingConfig
from embedder_client import EmbedderClient
from shared.features.build import build_movie_features
from shared.features.models import CatalogMovieInput, TmdbMetadata
from shared.features.to_document import features_to_lexical_document


def build_index_document(embedder: EmbedderClient, config: IndexingConfig, catalog_input: CatalogMovieInput,
    *, tmdb: TmdbMetadata | None = None, pipeline_version: str | None = None) -> dict[str, Any]:
    """
    Build one OpenSearch document with lexical fields and an embedding vector.

    Do this by:
    1. Building derived movie features from catalog input and optional TMDB metadata.
    2. Mapping features to the lexical OpenSearch document shape.
    3. Calling the embedder for a single-vector batch.
    4. Attaching embedding, embedding_model, and embedding_text to the doc.

    ============================ Arguments ============================
    embedder: Client for the embedder HTTP API.
    config: Indexing config with model id and pipeline version.
    catalog_input: Normalized catalog fields for one movie.
    tmdb: Optional TMDB metadata from Redis or a live fetch.
    pipeline_version: Optional pipeline version override.

    ============================ Returns ============================
    Complete OpenSearch document body ready for index/bulk.
    """
    # Build derived lexical and embedding features.
    features = build_movie_features(catalog_input, tmdb=tmdb)
    doc = features_to_lexical_document(
        features,
        pipeline_version or config.pipeline_version,
    )

    # Request one embedding vector from the embedder service.
    vectors = embedder.embed_texts([features.embedding_text])
    doc["embedding"] = vectors[0]
    doc["embedding_model"] = config.embedding_model_id
    doc["embedding_text"] = features.embedding_text

    return doc


def build_index_documents_batch(embedder: EmbedderClient, config: IndexingConfig, \
                                rows: list[tuple[CatalogMovieInput, TmdbMetadata | None]]) -> list[dict[str, Any]]:
    """
    Build multiple index documents with batched embedder calls.

    Do this by:
    1. Building features for every catalog row.
    2. Collecting embedding_text for each row.
    3. Calling embed_texts in chunks of config.embed_batch_size.
    4. Attaching vectors and metadata to each document.

    ============================ Arguments ============================
    embedder: Client for the embedder HTTP API.
    config: Indexing config with batch size and model id.
    rows: Pairs of catalog input and optional TMDB metadata.

    ============================ Returns ============================
    OpenSearch document bodies in the same order as rows.
    """
    # Check if the rows are empty and return an empty list.
    if not rows:
        return []

    # Initialize an empty list to store the lexical documents.
    lexical_docs = []
    # Initialize an empty list to store the embedding texts.
    embedding_texts = []

    # Loop through the rows and build the lexical and embedding features.
    for catalog_input, tmdb in rows:
        # Build the lexical and embedding features.
        features = build_movie_features(catalog_input, tmdb=tmdb)
        # Map the features to the lexical OpenSearch document shape.
        doc = features_to_lexical_document(features, config.pipeline_version)
        # Add the lexical document to the list.
        lexical_docs.append(doc)
        embedding_texts.append(features.embedding_text)

    # Initialize an empty list to store the embedding vectors.
    all_vectors = []
    batch_size = config.embed_batch_size
    # Loop through the embedding texts and embed them in chunks.
    for start in range(0, len(embedding_texts), batch_size):
        # Get the chunk of embedding texts.
        chunk = embedding_texts[start : start + batch_size]
        # Embed the chunk of embedding texts.
        all_vectors.extend(embedder.embed_texts(chunk))
    
    result = []
    # Loop through the lexical documents, embedding texts and embedding vectors and add them to the result.
    result: list[dict[str, Any]] = []
    for doc, text, vector in zip(lexical_docs, embedding_texts, all_vectors):
        doc["embedding"] = vector
        doc["embedding_model"] = config.embedding_model_id
        doc["embedding_text"] = text
        result.append(doc)

    return result

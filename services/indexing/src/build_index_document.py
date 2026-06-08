"""Build full OpenSearch movie documents with lexical fields and embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import IndexingConfig
from embedding_text import build_embedding_text
from embedder_client import EmbedderClient
from shared.movie_document import build_movie_document


@dataclass(frozen=True)
class CatalogRowFields:
    """
    Catalog fields needed to build one index document.
    """
    movie_id: int
    title: str
    genres: list[str]
    year: int | None = None
    tags: list[str] | None = None


def build_index_document(embedder: EmbedderClient, config: IndexingConfig, *, movie_id: int, \
                        title: str, genres: list[str], year: int | None = None, tags: list[str] | None = None, \
                        ) -> dict[str, Any]:
    """
    Build one OpenSearch document with lexical fields and an embedding vector.

    Do this by:
    1. Building the lexical document via build_movie_document.
    2. Composing embedding_text from clean title, genres, tags, and year.
    3. Calling the embedder for a single-vector batch.
    4. Attaching embedding, embedding_model, and embedding_text to the doc.

    ============================ Arguments ============================
    embedder: Client for the embedder HTTP API.
    config: Indexing config with model id and pipeline version.
    movie_id: Movie primary key.
    title: Raw catalog title.
    genres: Genre list.
    year: Optional explicit year override.
    tags: Optional user tags.

    ============================ Returns ============================
    Complete OpenSearch document body ready for index/bulk.
    """
    # Build lexical search fields (title, genres, search_text, etc.).
    doc = build_movie_document(
        movie_id,
        title,
        genres,
        year=year,
        tags=tags,
        pipeline_version=config.pipeline_version,
    )

    # Compose the string we send to the sentence-transformer.
    text = build_embedding_text(
        clean_title=doc["clean_title"],
        genres=doc["genres"],
        tags=doc["tags"],
        year=doc["year"],
    )

    # Request one embedding vector from the embedder service.
    vectors = embedder.embed_texts([text])
    doc["embedding"] = vectors[0]
    doc["embedding_model"] = config.embedding_model_id
    doc["embedding_text"] = text

    return doc


def build_index_documents_batch(embedder: EmbedderClient, config: IndexingConfig, \
                                rows: list[CatalogRowFields]) -> list[dict[str, Any]]:
    """
    Build multiple index documents with batched embedder calls.

    Do this by:
    1. Building lexical documents for every row.
    2. Collecting embedding_text for each row.
    3. Calling embed_texts in chunks of config.embed_batch_size.
    4. Attaching vectors and metadata to each document.

    ============================ Arguments ============================
    embedder: Client for the embedder HTTP API.
    config: Indexing config with batch size and model id.
    rows: Catalog rows to convert.

    ============================ Returns ============================
    OpenSearch document bodies in the same order as rows.
    """
    if not rows:
        return []

    # Build the lexical documents and embedding texts for each row.
    lexical_docs: list[dict[str, Any]] = []
    embedding_texts: list[str] = []

    # Loop through each row and build the lexical document and embedding text.
    for row in rows:
        # Build the lexical document.
        doc = build_movie_document(
            row.movie_id,
            row.title,
            row.genres,
            year=row.year,
            tags=row.tags,
            pipeline_version=config.pipeline_version,
        )
        # Build the embedding text.
        text = build_embedding_text(
            clean_title=doc["clean_title"],
            genres=doc["genres"],
            tags=doc["tags"],
            year=doc["year"],
        )
        # Add the lexical document and embedding text to the lists.
        lexical_docs.append(doc)
        embedding_texts.append(text)

    
    all_vectors: list[list[float]] = []
    batch_size = config.embed_batch_size
    # Loop through the embedding texts in chunks of batch_size and get the embedding vectors.
    for start in range(0, len(embedding_texts), batch_size):
        # Get the chunk of embedding texts.
        chunk = embedding_texts[start : start + batch_size]
        # Get the embedding vectors for the chunk.
        all_vectors.extend(embedder.embed_texts(chunk))

    result: list[dict[str, Any]] = []
    for doc, text, vector in zip(lexical_docs, embedding_texts, all_vectors):
        doc["embedding"] = vector
        doc["embedding_model"] = config.embedding_model_id
        doc["embedding_text"] = text
        result.append(doc)

    return result

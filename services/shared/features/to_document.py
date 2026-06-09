"""Map MovieFeatures to OpenSearch lexical document bodies."""

from __future__ import annotations

from typing import Any

from shared.features.models import MovieFeatures


def _optional_tmdb_fields(features: MovieFeatures) -> dict[str, Any]:
    """
    Build optional TMDB scalar fields for the OpenSearch document.

    Omit keys when values are missing so API-only rows without TMDB data stay
    compatible with the base lexical shape.

    ============================ Arguments ============================
    features: Derived movie features from build_movie_features.

    ============================ Returns ============================
    Dict of TMDB scalar fields to merge into the document body.
    """
    fields = {}

    if features.tmdb_id is not None:
        fields["tmdb_id"] = features.tmdb_id
    if features.popularity is not None:
        fields["popularity"] = features.popularity
    if features.vote_average is not None:
        fields["vote_average"] = features.vote_average
    if features.vote_count is not None:
        fields["vote_count"] = features.vote_count
    if features.runtime is not None:
        fields["runtime"] = features.runtime
    if features.original_language:
        fields["original_language"] = features.original_language
    if features.tmdb_keywords:
        fields["tmdb_keywords"] = features.tmdb_keywords

    return fields


def features_to_lexical_document(
    features: MovieFeatures,
    pipeline_version: str,
) -> dict[str, Any]:
    """
    Map derived features to the OpenSearch lexical document shape.

    ============================ Arguments ============================
    features: Derived movie features from build_movie_features.
    pipeline_version: Pipeline version stored on each indexed document.

    ============================ Returns ============================
    Lexical OpenSearch document fields without embedding vectors.
    """
    # Build an open search document with the features.
    doc = {
        "movie_id": features.movie_id,
        "title": features.title,
        "clean_title": features.clean_title,
        "year": features.year,
        "genres": features.genres,
        "tags": features.tags,
        "pipeline_version": pipeline_version,
    }

    if features.overview.strip():
        doc["overview"] = features.overview.strip()
    if features.tagline.strip():
        doc["tagline"] = features.tagline.strip()

    doc.update(_optional_tmdb_fields(features))
    return doc

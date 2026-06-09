"""Map OpenSearch document sources to API movie hit dicts."""

from __future__ import annotations

from typing import Any


def movie_hit_from_source(source: dict[str, Any], score: float | None) -> dict[str, Any]:
    """
    Build a movie hit dict from an indexed document source and relevance score.

    ============================ Arguments ============================
    source: OpenSearch _source for one movie document.
    score: OpenSearch relevance score, or None when not applicable.

    ============================ Returns ============================
    Dict aligned with recommender-api MovieHit fields.
    """
    return {
        "movie_id": source.get("movie_id"),
        "title": source.get("title"),
        "year": source.get("year"),
        "genres": source.get("genres", []),
        "overview": source.get("overview"),
        "tagline": source.get("tagline"),
        "vote_average": source.get("vote_average"),
        "vote_count": source.get("vote_count"),
        "popularity": source.get("popularity"),
        "score": score,
    }

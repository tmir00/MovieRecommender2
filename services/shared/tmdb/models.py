"""Parse TMDB API responses into feature metadata."""

from __future__ import annotations

from typing import Any

from shared.features.models import TmdbMetadata


def parse_tmdb_movie_response(body: dict[str, Any]) -> TmdbMetadata:
    """
    Map a TMDB movie details JSON body to TmdbMetadata.

    ============================ Arguments ============================
    body: JSON from GET /movie/{id}?append_to_response=keywords.

    ============================ Returns ============================
    Normalized TMDB metadata for feature engineering.
    """
    # Get the keywords from the TMDB API response.
    keywords_block = body.get("keywords") or {}
    
    # Get the keyword items from the keywords block.
    keyword_items = keywords_block.get("keywords") or []

    # Get the keywords from the keyword items.
    keywords = [
        str(item.get("name", "")).strip()
        for item in keyword_items
        if item.get("name")
    ]

    return TmdbMetadata(
        overview=str(body.get("overview") or "").strip(),
        tagline=str(body.get("tagline") or "").strip(),
        keywords=keywords,
        release_date=body.get("release_date") or None,
        popularity=_optional_float(body.get("popularity")),
        vote_average=_optional_float(body.get("vote_average")),
        vote_count=_optional_int(body.get("vote_count")),
        original_language=body.get("original_language") or None,
        runtime=_optional_int(body.get("runtime")),
    )


def tmdb_metadata_from_catalog_row(row: dict[str, Any]) -> TmdbMetadata | None:
    """
    Build TmdbMetadata from a catalog_movies Postgres row.

    Do this by:
    1. Checking whether enrich-tmdb has run (tmdb_enriched_at is set).
    2. Returning None when the row has not been enriched yet.
    3. Mapping catalog columns to TmdbMetadata for feature engineering.

    ============================ Arguments ============================
    row: Dict from catalog_movies fetch helpers.

    ============================ Returns ============================
    TmdbMetadata when the row has been TMDB-enriched; otherwise None.
    """
    if row.get("tmdb_enriched_at") is None:
        return None

    return TmdbMetadata(
        overview=str(row.get("overview") or "").strip(),
        tagline=str(row.get("tagline") or "").strip(),
        keywords=list(row.get("tmdb_keywords") or []),
        release_date=row.get("release_date"),
        popularity=_optional_float(row.get("popularity")),
        vote_average=_optional_float(row.get("vote_average")),
        vote_count=_optional_int(row.get("vote_count")),
        original_language=row.get("original_language"),
        runtime=_optional_int(row.get("runtime")),
    )


def catalog_tmdb_update_values(metadata: TmdbMetadata) -> dict[str, Any]:
    """
    Map TmdbMetadata to catalog_movies TMDB column values for UPDATE.

    ============================ Arguments ============================
    metadata: TMDB metadata from the API or an existing catalog row.

    ============================ Returns ============================
    Dict of column names and values for enrich UPDATE statements.
    """
    return {
        "overview": metadata.overview,
        "tagline": metadata.tagline,
        "tmdb_keywords": list(metadata.keywords),
        "popularity": metadata.popularity,
        "vote_average": metadata.vote_average,
        "vote_count": metadata.vote_count,
        "runtime": metadata.runtime,
        "original_language": metadata.original_language,
        "release_date": metadata.release_date,
    }


def tmdb_metadata_to_dict(metadata: TmdbMetadata) -> dict[str, Any]:
    """Serialize TmdbMetadata for JSON or Postgres-compatible storage."""
    return {
        "overview": metadata.overview,
        "tagline": metadata.tagline,
        "keywords": metadata.keywords,
        "release_date": metadata.release_date,
        "popularity": metadata.popularity,
        "vote_average": metadata.vote_average,
        "vote_count": metadata.vote_count,
        "original_language": metadata.original_language,
        "runtime": metadata.runtime,
    }


def tmdb_metadata_from_dict(data: dict[str, Any]) -> TmdbMetadata:
    """Deserialize TmdbMetadata from JSON or dict storage."""
    return TmdbMetadata(
        overview=str(data.get("overview") or ""),
        tagline=str(data.get("tagline") or ""),
        keywords=list(data.get("keywords") or []),
        release_date=data.get("release_date"),
        popularity=_optional_float(data.get("popularity")),
        vote_average=_optional_float(data.get("vote_average")),
        vote_count=_optional_int(data.get("vote_count")),
        original_language=data.get("original_language"),
        runtime=_optional_int(data.get("runtime")),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)

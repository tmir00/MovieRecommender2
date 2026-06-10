"""Postgres catalog_movies row adapter."""

from __future__ import annotations

from typing import Any

from shared.features.models import CatalogMovieInput


def row_to_catalog_input(row: dict[str, Any]) -> CatalogMovieInput:
    """
    Map one catalog_movies row to CatalogMovieInput.

    ============================ Arguments ============================
    row: Dict from fetch_pending_catalog_movies or fetch_catalog_movie_by_id.

    ============================ Returns ============================
    Normalized catalog input for feature engineering.
    """
    return CatalogMovieInput(
        movie_id=int(row["movie_id"]),
        title=row["title"],
        genres=list(row["genres"] or []),
        year=row["year"],
        tags=list(row["tags"] or []),
        tmdb_id=row.get("tmdb_id"),
    )

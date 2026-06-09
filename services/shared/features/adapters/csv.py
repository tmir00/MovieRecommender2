"""MovieLens CSV row adapter with links.csv TMDB join."""

from __future__ import annotations

from typing import Any

import pandas as pd

from shared.features.models import CatalogMovieInput
from shared.features.parsers import parse_ml_genres


def load_links_index(links_csv_path: str) -> dict[int, int]:
    """
    Build a movieId to tmdbId lookup from links.csv.

    ============================ Arguments ============================
    links_csv_path: Path to MovieLens links.csv.

    ============================ Returns ============================
    Mapping of MovieLens movieId to TMDB tmdbId for rows with valid ids.
    """
    links = pd.read_csv(links_csv_path, usecols=["movieId", "tmdbId"])
    index: dict[int, int] = {}

    for row in links.itertuples(index=False):
        movie_id = int(row.movieId)
        if pd.isna(row.tmdbId):
            continue
        tmdb_id = int(row.tmdbId)
        if tmdb_id > 0:
            index[movie_id] = tmdb_id

    return index


def row_to_catalog_input(row: Any, links_index: dict[int, int]) -> CatalogMovieInput:
    """
    Map one movies.csv row to CatalogMovieInput.

    ============================ Arguments ============================
    row: Pandas namedtuple from movies.csv.
    links_index: movieId to tmdbId mapping from load_links_index.

    ============================ Returns ============================
    Normalized catalog input with optional tmdb_id.
    """
    movie_id = int(row.movieId)
    return CatalogMovieInput(
        movie_id=movie_id,
        title=str(row.title),
        genres=parse_ml_genres(row.genres),
        tmdb_id=links_index.get(movie_id),
    )

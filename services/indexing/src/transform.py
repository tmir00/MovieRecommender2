"""Transform MovieLens movies.csv rows into catalog fields for indexing."""

from __future__ import annotations

from typing import Any

import pandas as pd

from build_index_document import CatalogRowFields


def parse_genres(raw_genres: str) -> list[str]:
    """Split pipe-separated genres into a list for keyword filtering."""
    if not raw_genres or (isinstance(raw_genres, float) and pd.isna(raw_genres)):
        return []
    return [genre.strip() for genre in str(raw_genres).split("|") if genre.strip()]


def row_to_index_fields(row: Any) -> CatalogRowFields:
    """
    Map one movies.csv row to catalog fields for index document building.

    ============================ Arguments ============================
    row: A pandas namedtuple or row object from movies.csv.

    ============================ Returns ============================
    CatalogRowFields with movie_id, title, and genres.
    """
    return CatalogRowFields(
        movie_id=int(row.movieId),
        title=str(row.title),
        genres=parse_genres(row.genres),
    )

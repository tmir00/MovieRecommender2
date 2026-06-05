"""Transform MovieLens movies.csv rows into OpenSearch documents."""

from __future__ import annotations

from typing import Any

import pandas as pd

from shared.movie_document import build_movie_document


def parse_genres(raw_genres: str) -> list[str]:
    """Split pipe-separated genres into a list for keyword filtering."""
    if not raw_genres or (isinstance(raw_genres, float) and pd.isna(raw_genres)):
        return []
    return [genre.strip() for genre in str(raw_genres).split("|") if genre.strip()]


def row_to_document(row: Any, pipeline_version: str) -> dict[str, Any]:
    """Map one movies.csv row to an OpenSearch document body."""
    title = str(row.title)
    return build_movie_document(
        movie_id=int(row.movieId),
        title=title,
        genres=parse_genres(row.genres),
        pipeline_version=pipeline_version,
    )

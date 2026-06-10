"""Parse and normalize raw catalog fields."""

from __future__ import annotations

import re

import pandas as pd

_TITLE_YEAR_RE = re.compile(r"^(?P<title>.+?)\s*\((?P<year>\d{4})\)\s*$")


def parse_title_year(raw_title: str) -> tuple[str, int | None]:
    """
    Split 'Toy Story (1995)' into clean title and year.

    ============================ Arguments ============================
    raw_title: Catalog title, optionally with trailing year in parentheses.

    ============================ Returns ============================
    Clean title and parsed year, or None when year is not in the title.
    E.g: 
    "Toy Story (1995)" -> ("Toy Story", 1995)
    """
    match = _TITLE_YEAR_RE.match(raw_title.strip())
    if not match:
        return raw_title.strip(), None
    return match.group("title").strip(), int(match.group("year"))


def resolve_year(title: str, explicit_year: int | None) -> int | None:
    """
    Prefer an explicit year; otherwise parse it from the title string.
    This is used to resolve the year of a movie when it is not provided by the caller.

    ============================ Arguments ============================
    title: Raw catalog title.
    explicit_year: Year provided by the caller, if any.

    ============================ Returns ============================
    Resolved release year or None.
    """
    if explicit_year is not None:
        return explicit_year
    _, parsed = parse_title_year(title)
    return parsed


def parse_ml_genres(raw_genres: str) -> list[str]:
    """
    Split MovieLens pipe-separated genres into a keyword list.

    ============================ Arguments ============================
    raw_genres: Genres column from movies.csv.

    ============================ Returns ============================
    Stripped genre labels.
    """
    # Check if the raw genres are empty or None.
    if not raw_genres or (isinstance(raw_genres, float) and pd.isna(raw_genres)):
        return []
    # Split the raw genres by the pipe character and return the list of genres.
    return [genre.strip() for genre in str(raw_genres).split("|") if genre.strip()]

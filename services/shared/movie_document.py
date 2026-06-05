"""Build OpenSearch movie document bodies from catalog fields."""

from __future__ import annotations

import re
from typing import Any

_TITLE_YEAR_RE = re.compile(r"^(?P<title>.+?)\s*\((?P<year>\d{4})\)\s*$")


def parse_title_year(raw_title: str) -> tuple[str, int | None]:
    """Split 'Toy Story (1995)' into clean title and year."""
    match = _TITLE_YEAR_RE.match(raw_title.strip())
    if not match:
        return raw_title.strip(), None
    return match.group("title").strip(), int(match.group("year"))


def build_movie_document(
    movie_id: int,
    title: str,
    genres: list[str],
    *,
    year: int | None = None,
    tags: list[str] | None = None,
    pipeline_version: str = "v1",
) -> dict[str, Any]:
    """Map catalog fields to an OpenSearch document body."""
    clean_title, parsed_year = parse_title_year(title)
    resolved_year = year if year is not None else parsed_year
    genre_list = list(genres)
    tag_list = list(tags or [])

    search_parts = [clean_title, *genre_list]
    if resolved_year is not None:
        search_parts.append(str(resolved_year))

    return {
        "movie_id": movie_id,
        "title": title,
        "clean_title": clean_title,
        "year": resolved_year,
        "genres": genre_list,
        "tags": tag_list,
        "search_text": " ".join(search_parts),
        "pipeline_version": pipeline_version,
    }

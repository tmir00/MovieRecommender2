"""Build the text string sent to the embedder for each movie."""

from __future__ import annotations


def build_embedding_text(*, clean_title: str, genres: list[str], tags: list[str], \
                            year: int | None) -> str:
    """
    Compose a pipe-delimited string for sentence-transformer encoding.

    We embed clean title plus metadata (genres, tags, year), not the raw
    catalog title like "Toy Story (1995)", so vectors reflect semantic content
    without redundant year parentheses.

    Do this by:
    1. Collecting non-empty parts: clean title, genres, tags, and year string.
    2. Joining them with " | " separators.

    ============================ Arguments ============================
    clean_title: Title with trailing year parentheses removed.
    genres: Genre labels for the movie.
    tags: User tags (may be empty for CSV bootstrap rows).
    year: Release year, or None if unknown.

    ============================ Returns ============================
    A single line suitable for POST /embed.

    # TODO
    """
    parts: list[str] = []
    if clean_title.strip():
        parts.append(clean_title.strip())
    parts.extend(g for g in genres if g)
    parts.extend(t for t in tags if t)
    if year is not None:
        parts.append(str(year))
    return " | ".join(parts)

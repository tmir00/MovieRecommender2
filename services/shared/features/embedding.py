"""Build the text string sent to the embedder for each movie."""

from __future__ import annotations

from shared.features.models import TmdbMetadata

OVERVIEW_EMBED_MAX_CHARS = 512


def truncate_overview_for_embed(overview: str, max_chars: int = OVERVIEW_EMBED_MAX_CHARS) -> str:
    """
    Trim overview text before adding it to embedding_text.

    ============================ Arguments ============================
    overview: Full TMDB overview text.
    max_chars: Maximum characters to keep.

    ============================ Returns ============================
    Truncated overview suitable for embedding.
    """
    # Strip the overview of leading/trailing whitespace and check if it is longer than the maximum 
    # characters.
    text = overview.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() # Return the truncated overview.

def build_embedding_text(*, clean_title: str, genres: list[str], tags: list[str], \
                            tmdb: TmdbMetadata | None = None) -> str:
    """
    Compose a pipe-delimited string for sentence-transformer encoding. This string will be used to 
    embed the movie in the database.

    We embed clean title plus metadata (genres, tags, TMDB text), not the
    raw catalog title like "Toy Story (1995)", so vectors reflect semantic content
    without redundant year parentheses.

    Do this by:
    1. Collecting non-empty parts: clean title, genres, and tags.
    2. Appending TMDB tagline, truncated overview, and keywords when present.
    3. Joining them with " | " separators.

    ============================ Arguments ============================
    clean_title: Title with trailing year parentheses removed.
    genres: Genre labels for the movie.
    tags: User tags (may be empty for CSV bootstrap rows).
    tmdb: Optional TMDB metadata to enrich the embedding input.

    ============================ Returns ============================
    A single line suitable for POST /embed.
    
    E.g: 
    clean_title | genre1 | genre2 | ... | tag1 | tag2 | ... | tagline | overview_snippet | kw1 | kw2 | ...
    """
    parts = []

    if clean_title.strip():
        parts.append(clean_title.strip())

    parts.extend(g for g in genres if g)
    parts.extend(t for t in tags if t)

    # Check if the TMDB metadata is not empty and add it to the parts.
    if tmdb is not None:
        
        # Check if the tagline is not empty and add it to the parts.
        if tmdb.tagline.strip():
            parts.append(tmdb.tagline.strip())
        
        # Truncate the overview and add it to the parts.
        overview = truncate_overview_for_embed(tmdb.overview)

        # Check if the overview is not empty and add it to the parts.
        if overview:
            parts.append(overview)
        
        # Add the keywords to the parts.
        parts.extend(k for k in tmdb.keywords if k)

    return " | ".join(parts)

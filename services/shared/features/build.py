"""Build derived movie features from catalog input."""

from __future__ import annotations

from shared.features.embedding import build_embedding_text
from shared.features.parsers import parse_title_year, resolve_year
from shared.features.models import CatalogMovieInput, MovieFeatures, TmdbMetadata


def build_movie_features(catalog_input: CatalogMovieInput, tmdb: TmdbMetadata | None = None) -> MovieFeatures:
    """
    Build movie features for OpenSearch. This function will be used to build the lexical and embedding 
    features for one movie as well as the serving features for the Model.

    Do this by:
    1. Resolving clean title and year from catalog input.
    2. Building embedding_text, optionally enriched with TMDB data.
    3. Returning a MovieFeatures object for document assembly.

    ============================ Arguments ============================
    catalog_input: Normalized movie fields from any source (e.g. CSV, API, etc.).
    tmdb: Optional TMDB metadata from Redis or a live fetch.

    ============================ Returns ============================
    Derived serving features for OpenSearch indexing.
    """
    #
    # Parse the title and year from the catalog input.
    clean_title, parsed_year = parse_title_year(catalog_input.title)
    # Resolve the year from the catalog input.
    year = resolve_year(catalog_input.title, catalog_input.year or parsed_year)
    # Get the genres from the catalog input.
    genres = list(catalog_input.genres)
    # Get the tags from the catalog input.
    tags = list(catalog_input.tags or [])

    # Get the TMDB metadata from the catalog input.
    overview = tmdb.overview if tmdb else ""
    tagline = tmdb.tagline if tmdb else ""
    keywords = list(tmdb.keywords) if tmdb else []

    embedding_text = build_embedding_text(
        clean_title=clean_title,
        genres=genres,
        tags=tags,
        tmdb=tmdb,
    )

    # Return the movie features.
    return MovieFeatures(
        movie_id=catalog_input.movie_id,
        title=catalog_input.title,
        clean_title=clean_title,
        year=year,
        genres=genres,
        tags=tags,
        embedding_text=embedding_text,
        overview=overview,
        tagline=tagline,
        tmdb_keywords=keywords,
        tmdb_id=catalog_input.tmdb_id,
        popularity=tmdb.popularity if tmdb else None,
        vote_average=tmdb.vote_average if tmdb else None,
        vote_count=tmdb.vote_count if tmdb else None,
        original_language=tmdb.original_language if tmdb else None,
        runtime=tmdb.runtime if tmdb else None,
    )

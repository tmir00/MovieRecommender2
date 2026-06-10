"""Canonical input and output types for movie feature engineering."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CatalogMovieInput:
    """
    Normalized catalog fields every ingest path must produce before feature engineering.
    """
    movie_id: int
    title: str
    genres: list[str]
    year: int | None = None
    tags: list[str] | None = None
    tmdb_id: int | None = None


@dataclass(frozen=True)
class TmdbMetadata:
    """
    TMDB movie metadata used to enrich lexical and embedding features.
    """
    overview: str = ""
    tagline: str = ""
    keywords: list[str] = field(default_factory=list)
    release_date: str | None = None
    popularity: float | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    original_language: str | None = None
    runtime: int | None = None


@dataclass(frozen=True)
class MovieFeatures:
    """
    Derived serving features for one movie document.
    """
    movie_id: int
    title: str
    clean_title: str
    year: int | None
    genres: list[str]
    tags: list[str]
    embedding_text: str
    overview: str = ""
    tagline: str = ""
    tmdb_keywords: list[str] = field(default_factory=list)
    tmdb_id: int | None = None
    popularity: float | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    original_language: str | None = None
    runtime: int | None = None

"""Pydantic schemas for catalog routes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateMovieRequest(BaseModel):
    """
    Request body for creating a new movie in the catalog.
    """
    movie_id: int | None = None
    title: str = Field(min_length=1)
    genres: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1888, le=2100)


class MovieResponse(BaseModel):
    """
    Response body for creating a new movie in the catalog.
    """
    movie_id: int
    title: str
    genres: list[str]
    year: int | None
    pending_opensearch_sync: bool
    opensearch_synced: bool = False


class PendingSyncResponse(BaseModel):
    """
    Response body for the pending sync count.
    """
    # The number of movies that are pending sync to the OpenSearch cluster.
    pending_count: int

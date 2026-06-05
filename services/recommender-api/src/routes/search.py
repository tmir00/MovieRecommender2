"""Movie search routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from config import RecommenderApiConfig
from opensearchpy import OpenSearch
from queries.search import search_movies


class MovieHit(BaseModel):
    movie_id: int
    title: str
    year: int | None = None
    genres: list[str] = []
    score: float | None = None


class SearchResponse(BaseModel):
    query: str
    total_returned: int
    results: list[MovieHit]


def create_search_router(config: RecommenderApiConfig, client: OpenSearch) -> APIRouter:
    router = APIRouter(tags=["search"])

    @router.get("/search", response_model=SearchResponse)
    def search(
        q: str = Query("", description="Full-text search query"),
        genre: str | None = Query(None, description="Exact genre filter"),
        year_from: int | None = Query(None, ge=1888, le=2100),
        year_to: int | None = Query(None, ge=1888, le=2100),
        size: int = Query(10, ge=1, le=100),
    ) -> dict[str, Any]:
        hits = search_movies(
            client,
            config,
            q=q,
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            size=size,
        )
        return {
            "query": q,
            "total_returned": len(hits),
            "results": hits,
        }

    return router

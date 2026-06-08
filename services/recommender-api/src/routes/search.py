"""Movie search routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from clients.embedder import EmbedderClient
from config import RecommenderApiConfig
from opensearchpy import OpenSearch
from queries.search import (
    search_movies,
    search_similar_by_movie_id,
    search_similar_by_text,
)


class MovieHit(BaseModel):
    """This the response body for the movie hit from the OpenSearch search results."""
    movie_id: int
    title: str
    year: int | None = None
    genres: list[str] = []
    score: float | None = None


class SearchResponse(BaseModel):
    """This is the response body for the search endpoint."""
    query: str
    total_returned: int
    results: list[MovieHit]


class SimilarSearchResponse(BaseModel):
    """Response body for vector similarity search."""
    mode: str
    query: str | None = None
    movie_id: int | None = None
    total_returned: int
    results: list[MovieHit]


def create_search_router(config: RecommenderApiConfig, client: OpenSearch, embedder: EmbedderClient) -> APIRouter:
    """
    Create the search router and provide the endpoint handlers with the configuration which includes the
    movies alias and the pipeline version, and the OpenSearch client to interact with the OpenSearch cluster.

    ============================ Arguments ============================
    config: The configuration for the recommender API.
    client: The OpenSearch client.
    embedder: Client for the embedder HTTP API.

    ============================ Returns ============================
    The search router.
    """
    router = APIRouter(tags=["search"])

    @router.get("/search", response_model=SearchResponse)
    def search(q: str = Query("", description="Full-text search query"), \
                genre: str | None = Query(None, description="Exact genre filter"), \
                year_from: int | None = Query(None, ge=1888, le=2100), \
                year_to: int | None = Query(None, ge=1888, le=2100), \
                size: int = Query(10, ge=1, le=100),) -> dict[str, Any]:
        """
        Search for movies in the catalog.

        ============================ Arguments ============================
        q: The full-text search query.
        genre: The exact genre filter.
        year_from: The lower bound for the movie release year.
        year_to: The upper bound for the movie release year.
        size: The maximum number of search results to return.

        ============================ Returns ============================
        The response body containing the search results.
        """
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

    @router.get("/search/similar", response_model=SimilarSearchResponse)
    def search_similar(
        q: str | None = Query(None, description="Free-text query for similar movies"),
        movie_id: int | None = Query(None, ge=1, description="Find movies similar to this id"),
        size: int = Query(10, ge=1, le=100),
    ) -> dict[str, Any]:
        """
        Find semantically similar movies using vector search.

        Provide either q (embed query text) or movie_id (use stored embedding).

        Do this by:
        1. Checking if either q or movie_id is provided.
        2. If q is provided, embed the query text and run the kNN search.
        3. If movie_id is provided, use the stored embedding to run the kNN search.
        4. Return the results.

        ============================ Arguments ============================
        q: Free-text query to embed and search.
        movie_id: Source movie id whose neighbors to return.
        size: Maximum number of results.

        ============================ Returns ============================
        Similar movies ranked by vector similarity score.
        """
        # Check if either q or movie_id is provided.
        if (q is None or not q.strip()) and movie_id is None:
            raise HTTPException(
                status_code=400,
                detail="Provide either q or movie_id",
            )
        # Check if both q and movie_id are provided.
        if q and q.strip() and movie_id is not None:
            raise HTTPException(
                status_code=400,
                detail="Provide only one of q or movie_id",
            )

        # If movie_id is provided, return the n most similar movies to it.
        if movie_id is not None:
            # Try to get the similar movies using the stored embedding.
            try:
                hits = search_similar_by_movie_id(
                    client,
                    config,
                    embedder,
                    movie_id=movie_id,
                    size=size,
                )
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            return {
                "mode": "movie_id",
                "query": None,
                "movie_id": movie_id,
                "total_returned": len(hits),
                "results": hits,
            }

        # If q is provided, embed the query text and run the kNN search.
        hits = search_similar_by_text(
            client,
            config,
            embedder,
            q=q or "",
            size=size,
        )

        return {
            "mode": "text",
            "query": q,
            "movie_id": None,
            "total_returned": len(hits),
            "results": hits,
        }

    return router

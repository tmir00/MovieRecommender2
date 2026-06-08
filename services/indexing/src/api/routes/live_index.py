"""Live catalog indexing routes (single movie from Postgres to OpenSearch)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from opensearchpy import OpenSearch
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from config import IndexingConfig
from index_movie import index_movie_document
from shared.db.catalog import fetch_catalog_movie_by_id, mark_catalog_movies_synced


class IndexMovieResponse(BaseModel):
    """
    Response body for a live catalog movie index request.
    """
    movie_id: int
    opensearch_synced: bool
    error: str | None = None


def create_live_index_router(config: IndexingConfig, engine: Engine, os_client: OpenSearch) -> APIRouter:
    """
    Create the live catalog index router.

    Provide the endpoint handlers with the configuration which includes the
    movies alias and the pipeline version, the SQLAlchemy engine to read from
    the database, and the OpenSearch client to write movie documents.

    ============================ Arguments ============================
    config: The configuration for the catalog indexer.
    engine: The SQLAlchemy engine.
    os_client: The OpenSearch client.

    ============================ Returns ============================
    The live catalog index router.
    """
    router = APIRouter(tags=["catalog-index"])

    @router.post("/index/movie/{movie_id}", response_model=IndexMovieResponse)
    def index_movie(movie_id: int) -> IndexMovieResponse:
        """
        Index one catalog movie from Postgres into the movies OpenSearch alias.

        1. First, load the movie row from catalog_movies.
        2. Then, build and index the movie document into the movies alias.
        3. If indexing succeeded, mark the row as synced in Postgres.
        4. Finally, return whether OpenSearch indexing succeeded.

        ============================ Arguments ============================
        movie_id: The movie id to index.

        ============================ Returns ============================
        The response body with opensearch_synced and an optional error message.
        """
        # Load the movie row from the database.
        row = fetch_catalog_movie_by_id(engine, movie_id)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Movie with movie_id={movie_id} not found in catalog_movies",
            )

        # Index the movie document into the movies alias.
        synced, error = index_movie_document(
            os_client,
            config,
            movie_id=int(row["movie_id"]),
            title=row["title"],
            genres=list(row["genres"] or []),
            year=row["year"],
            tags=list(row["tags"] or []),
            pipeline_version=row["pipeline_version"],
        )

        # If the movie was successfully indexed, mark the movie as synced in the database.
        if synced:
            mark_catalog_movies_synced(engine, [movie_id])

        return IndexMovieResponse(
            movie_id=movie_id,
            opensearch_synced=synced,
            error=error,
        )

    return router

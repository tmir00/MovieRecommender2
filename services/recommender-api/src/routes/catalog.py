"""Catalog write routes."""

from __future__ import annotations

from sqlalchemy.engine import Engine
from config import RecommenderApiConfig
from fastapi import APIRouter, HTTPException, Query
from clients.catalog_indexer import CatalogIndexerClient
from shared.exceptions import CatalogMovieAlreadyExists
from schemas.catalog import CreateMovieRequest, MovieResponse, PendingSyncResponse
from shared.db.catalog import count_pending_catalog_sync, insert_catalog_movie


def create_catalog_router(config: RecommenderApiConfig, engine: Engine, catalog_indexer: CatalogIndexerClient) -> APIRouter:
    """
    Create the catalog router and provide the endpoint handlers with the configuration which includes the
    movies alias and the pipeline version, the SQLAlchemy engine to interact with the database, and the OpenSearch
    client to interact with the OpenSearch cluster.

    ============================ Arguments ============================
    config: The configuration for the recommender API.
    engine: The SQLAlchemy engine.
    os_client: The OpenSearch client.

    ============================ Returns ============================
    The catalog router.
    """
    # Create the router which will contain the catalog endpoints like /movies and /pending-sync.
    router = APIRouter(tags=["catalog"])

    @router.post("/movies", response_model=MovieResponse, status_code=201)
    def create_movie(body: CreateMovieRequest, \
                    sync: str | None = Query(default=None, description="Pass immediate=true to index the movie in OpenSearch immediately."), \
                    ) -> MovieResponse:
        """
        Create a new movie in the catalog.

        1. First, insert the movie into the database.
        2. Then, if the user wants to index the movie in OpenSearch immediately, index the movie document into the movies alias.
        3. Finally, return the movie information.

        ============================ Arguments ============================
        body: The request body containing the movie information.
        sync: Whether to index the movie in OpenSearch immediately.

        ============================ Returns ============================
        The response body containing the movie information.
        """
        # Check if the user wants to index the movie in OpenSearch immediately.
        immediate_sync = sync == "immediate=true"

        # Insert the movie into the database.
        try:
            movie_id, year = insert_catalog_movie(
                engine,
                movie_id=body.movie_id,
                title=body.title,
                genres=body.genres,
                year=body.year,
                pipeline_version=config.pipeline_version,
            )
        except CatalogMovieAlreadyExists as exc:
            raise HTTPException(
                status_code=409,
                detail=f"Movie with movie_id={exc.movie_id} already exists",
            ) from exc

        # If the user doesn't want to index the movie in OpenSearch immediately, return the movie information.
        if not immediate_sync:
            return MovieResponse(
                movie_id=movie_id,
                title=body.title,
                genres=body.genres,
                year=year,
                pending_opensearch_sync=True,
                opensearch_synced=False,
            )

        # If the user want's to immediately sync the movie in OpenSearch, index the movie document into the movies alias.
        synced, _error = catalog_indexer.index_movie(movie_id)
        # If the movie was successfully indexed, mark the movie as synced in the database.

        # Return the movie information.
        return MovieResponse(
            movie_id=movie_id,
            title=body.title,
            genres=body.genres,
            year=year,
            pending_opensearch_sync=not synced,
            opensearch_synced=synced,
        )

    @router.get("/catalog/pending-sync", response_model=PendingSyncResponse)
    def pending_sync() -> PendingSyncResponse:
        """
        Get the number of movies that are pending sync to the OpenSearch cluster from the database.

        ============================ Returns ============================
        The response body containing the number of movies that are pending sync to the OpenSearch cluster.
        """
        count = count_pending_catalog_sync(engine)
        return PendingSyncResponse(pending_count=count)

    return router

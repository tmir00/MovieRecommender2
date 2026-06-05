"""Catalog write routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, insert, select
from sqlalchemy.engine import Engine

from config import RecommenderApiConfig
from db.models import catalog_movies
from schemas.catalog import CreateMovieRequest, MovieResponse, PendingSyncResponse
from shared.movie_document import parse_title_year


def _resolve_year(title: str, explicit_year: int | None) -> int | None:
    if explicit_year is not None:
        return explicit_year
    _, parsed = parse_title_year(title)
    return parsed


def _next_movie_id(engine: Engine) -> int:
    with engine.connect() as conn:
        result = conn.execute(select(func.coalesce(func.max(catalog_movies.c.movie_id), 0)))
        current_max = result.scalar_one()
        return int(current_max) + 1


def create_catalog_router(config: RecommenderApiConfig, engine: Engine) -> APIRouter:
    router = APIRouter(tags=["catalog"])

    @router.post("/movies", response_model=MovieResponse, status_code=201)
    def create_movie(body: CreateMovieRequest) -> MovieResponse:
        movie_id = body.movie_id if body.movie_id is not None else _next_movie_id(engine)
        year = _resolve_year(body.title, body.year)

        with engine.begin() as conn:
            existing = conn.execute(
                select(catalog_movies.c.movie_id).where(
                    catalog_movies.c.movie_id == movie_id
                )
            ).first()
            if existing is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Movie with movie_id={movie_id} already exists",
                )

            conn.execute(
                insert(catalog_movies).values(
                    movie_id=movie_id,
                    title=body.title,
                    genres=body.genres,
                    year=year,
                    tags=[],
                    active=True,
                    pending_opensearch_sync=True,
                    pipeline_version=config.pipeline_version,
                )
            )

        return MovieResponse(
            movie_id=movie_id,
            title=body.title,
            genres=body.genres,
            year=year,
            pending_opensearch_sync=True,
        )

    @router.get("/catalog/pending-sync", response_model=PendingSyncResponse)
    def pending_sync() -> PendingSyncResponse:
        with engine.connect() as conn:
            result = conn.execute(
                select(func.count())
                .select_from(catalog_movies)
                .where(
                    catalog_movies.c.pending_opensearch_sync.is_(True),
                    catalog_movies.c.active.is_(True),
                )
            )
            count = int(result.scalar_one())
        return PendingSyncResponse(pending_count=count)

    return router

"""Live catalog indexer API — on-demand Postgres catalog_movies → OpenSearch."""

from __future__ import annotations

import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.routes.live_index import create_live_index_router
from config import IndexingConfig
from opensearch_client import get_opensearch_client
from shared.db.engine import create_engine_from_url
from shared.db.health import ping_postgres
from health import opensearch_ready


config = IndexingConfig.from_env()
engine = create_engine_from_url(config.database_url)
os_client = get_opensearch_client(config)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan manager for the catalog indexer API.
    """
    yield
    os_client.close()
    engine.dispose()


app = FastAPI(
    title="Catalog Indexer API",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.include_router(create_live_index_router(config, engine, os_client))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> JSONResponse:
    """
    Health check endpoint for the catalog indexer API.
    Check if the database and OpenSearch are reachable.

    ============================ Returns ============================
    A JSON response with the status of the health check.
    """
    if ping_postgres(engine) and opensearch_ready(os_client, config):
        return JSONResponse(content={"status": "ready"})
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": "postgres_or_opensearch_unavailable"},
    )


def main() -> None:
    """
    Run the catalog indexer API using uvicorn.

    ============================ Arguments ============================
    host: The host to run the API on.
    port: The port to run the API on.
    reload: Whether to reload the API when code changes are detected.
    """
    uvicorn.run(
        app,
        host=config.catalog_indexer_host,
        port=config.catalog_indexer_port,
        reload=False,
    )


if __name__ == "__main__":
    main()

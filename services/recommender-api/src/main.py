"""Recommender API — search, catalog writes; /recommend and /rate planned."""

from __future__ import annotations

import uvicorn

from fastapi import FastAPI
from db.session import get_engine
from shared.db.health import ping_postgres
from config import RecommenderApiConfig
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from queries.search import opensearch_ready
from routes.search import create_search_router
from routes.catalog import create_catalog_router
from opensearch_client import get_opensearch_client
from clients.catalog_indexer import CatalogIndexerClient


# Load the configuration and create the database and OpenSearch clients.
config = RecommenderApiConfig.from_env()
engine = get_engine()
os_client = get_opensearch_client(config)
catalog_indexer = CatalogIndexerClient(config.catalog_indexer_url)

# Check if the database is reachable.
def _postgres_ok() -> bool:
    """
    Connect to the database and execute a simple query to check if it is reachable.
    
    ============================ Returns ============================
    True if the database is reachable, False otherwise.
    """
    return ping_postgres(engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan manager for the FastAPI application.
    """
    # App starts, nothing special happens before yielding control to the FastAPI application.
    yield
    # App is shutting down, close the OpenSearch and database clients.
    os_client.close()
    engine.dispose()


# Create the FastAPI application.
app = FastAPI(
    title="Movie Recommender API",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Include the search and catalog routers.
app.include_router(create_search_router(config, os_client))
app.include_router(create_catalog_router(config, engine, catalog_indexer))

# Health check endpoints.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> JSONResponse:
    """
    Health check endpoint for the recommender API.
    Check if the database and OpenSearch are reachable.
    
    ============================ Returns ============================
    A JSON response with the status of the health check.
    """
    if _postgres_ok() and opensearch_ready(os_client, config):
        return JSONResponse(content={"status": "ready"})
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": "postgres_or_opensearch_unavailable"},
    )


def main() -> None:
    """
    Run the recommender API using uvicorn.
    
    ============================ Arguments ============================
    host: The host to run the API on.
    port: The port to run the API on.
    reload: Whether to reload the API when code changes are detected.
    """
    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()

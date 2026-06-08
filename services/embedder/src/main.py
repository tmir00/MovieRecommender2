"""Embedder API — sentence-transformer vectors over HTTP."""

from __future__ import annotations

import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import EmbedderConfig
from model import EmbeddingModel


config = EmbedderConfig.from_env()
_model: EmbeddingModel | None = None


class EmbedRequest(BaseModel):
    """
    Request body for the embed endpoint.
    """
    texts: list[str] = Field(min_length=1)


class EmbedResponse(BaseModel):
    """
    Response body for the embed endpoint.
    """
    embeddings: list[list[float]]
    model_id: str
    dimension: int


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan manager for the embedder API.

    Load the sentence-transformer model once at startup, then reuse it for all embed requests.
    """
    # Before yielding to the FastaAPI application, load the embedding model into memory.
    global _model
    _model = EmbeddingModel(config.embedding_model_id, config.embedding_dimension)
    yield


# Create the FastAPI application and include the lifespan manager.
app = FastAPI(
    title="Movie Embedder API",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> dict[str, str]:
    """
    ! Health check function.

    Report ready when the embedding model has been loaded into memory.

    ============================ Returns ============================
    A JSON object with status ready or not_ready.
    """
    if _model is None:
        return {"status": "not_ready"}
    return {"status": "ready"}


@app.post("/embed", response_model=EmbedResponse)
def embed(body: EmbedRequest) -> EmbedResponse:
    """
    Encode one or more texts into embedding vectors.

    Do this by:
    1. Validating that the model is loaded.
    2. Running batch encode on the request texts.
    3. Returning vectors with model metadata.

    ============================ Arguments ============================
    body: Request containing a list of strings to embed.

    ============================ Returns ============================
    Embeddings aligned with input texts plus model id and dimension.
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")

    # Encode all request texts in one model pass.
    vectors = _model.encode_texts(body.texts)

    return EmbedResponse(
        embeddings=vectors,
        model_id=config.embedding_model_id,
        dimension=config.embedding_dimension,
    )


def main() -> None:
    """
    Run the embedder API using uvicorn.

    ============================ Arguments ============================
    host: The host to run the API on.
    port: The port to run the API on.
    reload: Whether to reload the API when code changes are detected.
    """
    uvicorn.run(
        app,
        host=config.embedder_host,
        port=config.embedder_port,
        reload=False,
    )


if __name__ == "__main__":
    main()

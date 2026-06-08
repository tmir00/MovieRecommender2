"""HTTP client for the embedder service."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class EmbedderClient:
    """
    Call the embedder API to encode text batches into vectors.
    """

    def __init__(self, base_url: str, timeout: float = 120.0) -> None:
        """
        ============================ Arguments ============================
        base_url: Embedder service root URL (e.g. http://embedder:8100).
        timeout: HTTP request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Request embedding vectors for a batch of texts.

        Do this by:
        1. POSTing the texts to /embed on the embedder service.
        2. Parsing the embeddings array from the JSON response.

        ============================ Arguments ============================
        texts: Non-empty list of strings to encode.

        ============================ Returns ============================
        One embedding vector per input text.

        ============================ Raises ============================
        httpx.HTTPError: When the embedder request fails.
        ValueError: When the response shape does not match the request.
        """
        if not texts:
            return []

        # Send a POST request to the embedder service to get the embedding vectors.
        url = f"{self._base_url}/embed"
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, json={"texts": texts})
            # If the request is not successful, raise an exception. Otherwise, continue.
            response.raise_for_status()
            body = response.json()

        # Parse the response body.
        embeddings = body.get("embeddings")
        # If the response body is not a list or the length of the list does not match the length of the input texts, raise an exception.
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise ValueError(
                f"Embedder returned {len(embeddings) if isinstance(embeddings, list) else 0} "
                f"vectors for {len(texts)} texts"
            )
        return embeddings

    def ping(self) -> bool:
        """
        Check whether the embedder reports ready.

        ============================ Returns ============================
        True when GET /health/ready returns status ready.
        """
        url = f"{self._base_url}/health/ready"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json().get("status") == "ready"
        except httpx.HTTPError:
            logger.warning("Embedder health check failed", exc_info=True)
            return False

"""HTTP client for the live catalog indexer service."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class CatalogIndexerClient:
    """
    Call the catalog indexer API to index one movie into OpenSearch.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def index_movie(self, movie_id: int) -> tuple[bool, str | None]:
        """
        Request live indexing for one catalog movie.

        Do this by:
        1. Calling the catalog indexer POST /index/movie/{movie_id} endpoint.
        2. Returning whether OpenSearch indexing succeeded and any error message.

        ============================ Arguments ============================
        movie_id: The movie id to index.

        ============================ Returns ============================
        The success flag and optional error message from the indexer.
        """
        url = f"{self._base_url}/index/movie/{movie_id}"
        try:
            # Create a new HTTP client with a timeout of 60 seconds.
            with httpx.Client(timeout=60.0) as client:
                # Send a POST request to the catalog indexer API to index the movie.
                response = client.post(url)
            # If the movie is not found, return a failure and an error message.
            if response.status_code == 404:
                return False, f"Movie with movie_id={movie_id} not found in catalog_movies"
            # If the request is not successful, raise an exception.
            response.raise_for_status()
            # Parse the response body.
            body = response.json()
            # Return the success flag and optional error message from the indexer.
            synced = bool(body.get("opensearch_synced"))
            error = body.get("error")
            return synced, error
            
        # If there was an HTTP error, return a failure and the error message.
        except httpx.HTTPError as exc:
            logger.exception("Catalog indexer request failed for movie %s", movie_id)
            return False, str(exc)

        # If there was an exception, return a failure and the error message.
        except Exception as exc:
            logger.exception("Catalog indexer request failed for movie %s", movie_id)
            return False, str(exc)

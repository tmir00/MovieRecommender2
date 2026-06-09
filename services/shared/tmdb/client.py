"""HTTP client for the TMDB movie details API."""

from __future__ import annotations

import logging

import httpx

from shared.features.models import TmdbMetadata
from shared.tmdb.config import TmdbConfig
from shared.tmdb.models import parse_tmdb_movie_response

logger = logging.getLogger(__name__)


class TmdbClient:
    """
    Fetch movie metadata from TMDB with Bearer token authentication.
    """

    def __init__(self, config: TmdbConfig, timeout: float = 30.0) -> None:
        self._config = config
        self._timeout = timeout

    def fetch_movie(self, tmdb_id: int) -> TmdbMetadata | None:
        """
        Load one movie record from TMDB.

        Do this by:
        1. Calling GET /movie/{id} with keywords appended.
        2. Parsing the JSON body into TmdbMetadata.
        3. Returning None when TMDB responds with 404.

        ============================ Arguments ============================
        tmdb_id: TMDB movie identifier.

        ============================ Returns ============================
        Parsed metadata, or None when the movie is not found.
        """
        # Build the URL for the TMDB API.
        url = f"{self._config.tmdb_base_url.rstrip('/')}/movie/{tmdb_id}"
        
        # Build the parameters for the TMDB API.
        params = {
            "api_key": self._config.tmdb_api_key,
            "append_to_response": "keywords",
        }

        # Make the request to the TMDB API.
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(url, params=params)

        # Check if the response is a 404 and return None.
        if response.status_code == 404:
            logger.warning("TMDB movie not found", extra={"tmdb_id": tmdb_id})
            return None

        # Raise an exception if the response is not successful.
        response.raise_for_status()
        
        # Parse the response into a TmdbMetadata object.
        return parse_tmdb_movie_response(response.json())

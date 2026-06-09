"""TMDB and Postgres configuration for TMDB enrichment jobs."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TmdbConfig:
    """
    Runtime settings for TMDB fetch and Postgres catalog updates.
    """
    tmdb_api_key: str
    tmdb_base_url: str
    database_url: str
    tmdb_rate_limit_rps: float
    log_every_n_rows: int
    enrich_batch_size: int

    @classmethod
    def from_env(cls) -> TmdbConfig:
        """
        Load TMDB enrichment settings from the environment.

        ============================ Returns ============================
        TmdbConfig with API and Postgres connection settings.
        """
        api_key = os.environ.get("TMDB_API_KEY", "")
        if not api_key:
            raise ValueError("TMDB_API_KEY is required for TMDB enrichment")

        return cls(
            tmdb_api_key=api_key,
            tmdb_base_url=os.environ.get(
                "TMDB_BASE_URL",
                "https://api.themoviedb.org/3",
            ),
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgresql+psycopg://movierec:movierec@postgres:5432/movierec",
            ),
            tmdb_rate_limit_rps=float(os.environ.get("TMDB_RATE_LIMIT_RPS", "35")),
            log_every_n_rows=int(os.environ.get("LOG_EVERY_N_ROWS", "500")),
            enrich_batch_size=int(os.environ.get("TMDB_ENRICH_BATCH_SIZE", "500")),
        )

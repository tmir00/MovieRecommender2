"""Embedder service configuration."""

from __future__ import annotations

import os

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbedderConfig:
    """
    Runtime settings for the embedder API.
    """
    embedding_model_id: str
    embedding_dimension: int
    embedder_host: str
    embedder_port: int

    @classmethod
    def from_env(cls) -> EmbedderConfig:
        """
        Load settings from the environment.

        ============================ Returns ============================
        EmbedderConfig with model id, vector dimension, and bind host/port.
        """
        return cls(
            embedding_model_id=os.environ.get(
                "EMBEDDING_MODEL_ID",
                "sentence-transformers/all-MiniLM-L6-v2",
            ),
            embedding_dimension=int(os.environ.get("EMBEDDING_DIMENSION", "384")),
            embedder_host=os.environ.get("EMBEDDER_HOST", "0.0.0.0"),
            embedder_port=int(os.environ.get("EMBEDDER_PORT", "8100")),
        )

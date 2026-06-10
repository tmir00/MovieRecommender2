"""Load and run the sentence-transformer embedding model."""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wrap a Hugging Face sentence-transformer for batch text encoding.
    """

    def __init__(self, model_id: str, expected_dimension: int) -> None:
        """
        Load the model into memory.

        Do this by:
        1. Loading the model into memory.
        2. Probing the model to get the actual output vector size.
        3. Validating that the actual output vector size matches the expected output vector size.

        ============================ Arguments ============================
        model_id: Hugging Face model id (e.g. sentence-transformers/all-MiniLM-L6-v2).
        expected_dimension: Expected output vector size; validated after load.
        """
        # Store the model id and expected dimension.
        self.model_id = model_id
        self.dimension = expected_dimension

        # Load the model into memory.
        logger.info("Loading embedding model", extra={"model_id": model_id})
        self._model = SentenceTransformer(model_id)

        # Probe the model to get the actual output vector size.
        probe = self._model.encode(["probe"], normalize_embeddings=True)

        # Get the actual output vector size.
        actual_dim = len(probe[0])

        # If the actual output vector size does not match the expected output vector size, raise an exception.
        if actual_dim != expected_dimension:
            raise ValueError(
                f"Model {model_id} produced dimension {actual_dim}, "
                f"expected {expected_dimension}"
            )

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Encode a batch of texts into cosine-normalized embedding vectors.

        Do this by:
        1. Running the sentence-transformer encode pass on all texts.
        2. Converting each vector to a plain Python list of floats.

        ============================ Arguments ============================
        texts: Non-empty list of strings to embed.

        ============================ Returns ============================
        One embedding vector per input text, each of length self.dimension.
        """
        # If the list of texts is empty, return an empty list.
        if not texts:
            return []

        # Run the model and normalize so cosine similarity matches dot product in OpenSearch.
        vectors = self._model.encode(texts, normalize_embeddings=True)
        # Return a list of embedding vectors as lists of floats.
        return [vector.tolist() for vector in vectors]

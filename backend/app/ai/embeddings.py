import math
from collections.abc import Sequence

from google import genai

from backend.app.core.config import settings


class EmbeddingError(ValueError):
    """Raised when an embedding response is invalid or unavailable."""


def normalize_embedding(values: Sequence[float], dimension: int) -> list[float]:
    if len(values) != dimension:
        raise EmbeddingError(
            f"Expected embedding dimension {dimension}, received {len(values)}."
        )
    vector = [float(value) for value in values]
    if not all(math.isfinite(value) for value in vector):
        raise EmbeddingError("Embedding contains a non-finite value.")
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise EmbeddingError("Embedding has zero magnitude.")
    return [value / norm for value in vector]


class GeminiEmbedder:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dimension: int = 768,
    ) -> None:
        self.model = model
        self.dimension = dimension
        self.client = genai.Client(api_key=api_key)

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingError("Cannot embed empty text.")
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config={"output_dimensionality": self.dimension},
        )
        embeddings = response.embeddings or []
        if len(embeddings) != 1 or not embeddings[0].values:
            raise EmbeddingError("Gemini returned an invalid embedding response.")
        return normalize_embedding(embeddings[0].values, self.dimension)


def create_configured_embedder() -> GeminiEmbedder:
    if not settings.gemini_api_key:
        raise EmbeddingError("GEMINI_API_KEY is required for embedding operations.")
    return GeminiEmbedder(
        api_key=settings.gemini_api_key,
        model=settings.gemini_embedding_model,
        dimension=settings.embedding_dimension,
    )

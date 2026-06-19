"""all-MiniLM-L6-v2 embeddings (384 dims). Ported from Recourse's rag_service.py.

The model is loaded lazily (first call) so importing this module stays cheap.
"""
from __future__ import annotations

from config import settings

_model = None


def _get_model():
    """Load the embedding model once and reuse it."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
    return _model


def warm_up() -> None:
    """Eagerly load the embedding model so the CPU-heavy first load happens up front
    (before the agent serves a call) instead of blocking the event loop mid-debate."""
    _get_model()


def embed_text(text: str) -> list[float]:
    """Return a 384-dim embedding for a single string."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a batch of strings."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]

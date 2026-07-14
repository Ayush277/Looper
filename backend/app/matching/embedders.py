"""Embedding providers behind one interface (docs/06 D6).

OpenAI text-embedding-3-small when a key is present; automatic fallback to a
local sentence-transformers MiniLM otherwise (or on API failure). Vectors are
cached by the pipeline on the jobs/keywords rows, so providers are only hit
for *new* text.
"""
import asyncio
import math
from typing import Any, Protocol

import httpx
from loguru import logger

from app.config import get_settings

OPENAI_MODEL = "text-embedding-3-small"
LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    model_name: str

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    model_name = f"openai/{OPENAI_MODEL}"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": OPENAI_MODEL, "input": texts},
            )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]


class LocalEmbedder:
    """sentence-transformers MiniLM — zero-cost, offline, ~90MB model."""

    model_name = f"local/{LOCAL_MODEL}"

    def __init__(self) -> None:
        self._model: Any = None

    def _load(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("loading local embedding model {}", LOCAL_MODEL)
            self._model = SentenceTransformer(LOCAL_MODEL)
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = await asyncio.to_thread(self._load)
        vectors = await asyncio.to_thread(
            model.encode, texts, show_progress_bar=False, normalize_embeddings=True
        )
        return [v.tolist() for v in vectors]


class FallbackEmbedder:
    """OpenAI first, local on any failure — the pipeline never dies for lack
    of an API key (NFR-11)."""

    def __init__(self, primary: Embedder, fallback: Embedder):
        self._primary = primary
        self._fallback = fallback
        self.model_name = primary.model_name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return await self._primary.embed(texts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("primary embedder failed ({}), using local fallback", exc)
            self.model_name = self._fallback.model_name
            return await self._fallback.embed(texts)


def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.openai_api_key:
        return FallbackEmbedder(OpenAIEmbedder(settings.openai_api_key), LocalEmbedder())
    return LocalEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

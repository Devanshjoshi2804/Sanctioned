"""Retrieval backends.

``TfidfRetriever`` is a pure-Python, dependency-free, deterministic retriever used
by default and in CI. ``GeminiRetriever`` embeds the corpus and queries with
Gemini when a key is configured. Both rank documents by cosine similarity and
share the same interface, so the copilot is agnostic to which is in use.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

from sanctioned_copilot.corpus import Document

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [tok for tok in _TOKEN.findall(text.lower()) if len(tok) > 1]


class Retriever(Protocol):
    """Ranks corpus documents against a query."""

    def search(self, query: str, k: int) -> list[tuple[Document, float]]: ...


class TfidfRetriever:
    """Classic TF-IDF cosine retrieval over the corpus, in pure Python."""

    def __init__(self, documents: list[Document]) -> None:
        self._documents = documents
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        self._index()

    def _index(self) -> None:
        n = len(self._documents)
        df: Counter[str] = Counter()
        tokenized = [_tokenize(d.text) for d in self._documents]
        for tokens in tokenized:
            df.update(set(tokens))
        self._idf = {term: math.log((n + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}
        self._vectors = [self._vectorize(tokens) for tokens in tokenized]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        vector = {
            term: (1.0 + math.log(count)) * self._idf.get(term, 0.0)
            for term, count in counts.items()
        }
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        if norm == 0:
            return {}
        return {term: weight / norm for term, weight in vector.items()}

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        query_vector = self._vectorize(_tokenize(query))
        scored = [
            (doc, _cosine_sparse(query_vector, vec))
            for doc, vec in zip(self._documents, self._vectors, strict=True)
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


def _cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    # Both vectors are L2-normalised, so cosine is just the dot product.
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    return sum(weight * larger.get(term, 0.0) for term, weight in smaller.items())


class GeminiRetriever:
    """Embeds the corpus and queries with Gemini, ranking by cosine similarity."""

    def __init__(self, documents: list[Document], *, api_key: str, model: str) -> None:
        from google import genai  # lazy import keeps the offline path dependency-free

        self._documents = documents
        self._model = model
        self._client = genai.Client(api_key=api_key)
        self._vectors = [_normalize(self._embed(doc.text)) for doc in documents]

    def _embed(self, text: str) -> list[float]:
        result = self._client.models.embed_content(model=self._model, contents=text)
        embeddings = result.embeddings
        if not embeddings or embeddings[0].values is None:
            raise RuntimeError("Gemini returned an empty embedding")
        return list(embeddings[0].values)

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        query_vector = _normalize(self._embed(query))
        scored = [
            (doc, _dot(query_vector, vec))
            for doc, vec in zip(self._documents, self._vectors, strict=True)
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))

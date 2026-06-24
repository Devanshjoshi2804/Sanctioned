"""The copilot facade: build the corpus, retrieve, answer, and cite.

Backend selection is automatic. With ``GEMINI_API_KEY`` set, the copilot embeds
and synthesises with Gemini; otherwise it falls back to the offline TF-IDF
retriever and extractive answerer. Either way, every answer is accompanied by the
citations it was grounded in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sanctioned.registry import Registry, bundled_policies_dir, load_bundled_registry
from sanctioned_copilot.answerer import Answerer, ExtractiveAnswerer, GeminiAnswerer
from sanctioned_copilot.corpus import build_corpus
from sanctioned_copilot.retriever import GeminiRetriever, Retriever, TfidfRetriever

_DEFAULT_EMBED_MODEL = "gemini-embedding-001"
_DEFAULT_GEN_MODEL = "gemini-flash-latest"


@dataclass(frozen=True)
class Citation:
    """A pointer back to the source a passage came from."""

    citation: str
    source: str
    section: str
    score: float


@dataclass(frozen=True)
class Answer:
    """A grounded answer with its supporting citations."""

    question: str
    answer: str
    citations: tuple[Citation, ...]
    backend: str


class Copilot:
    """Retrieval-augmented Q&A over the policy registry and runbook."""

    def __init__(self, retriever: Retriever, answerer: Answerer, *, backend: str) -> None:
        self._retriever = retriever
        self._answerer = answerer
        self._backend = backend

    @property
    def backend(self) -> str:
        """Which backend is active: ``"gemini"`` or ``"offline"``."""
        return self._backend

    @classmethod
    def build(
        cls,
        registry: Registry | None = None,
        docs_dir: Path | None = None,
        *,
        prefer_live: bool = True,
    ) -> Copilot:
        """Build a copilot, choosing the Gemini backend when a key is available."""
        registry = registry or load_bundled_registry()
        docs_dir = docs_dir or (bundled_policies_dir().parent.parent.parent / "docs")
        documents = build_corpus(registry, docs_dir)

        api_key = os.environ.get("GEMINI_API_KEY")
        if prefer_live and api_key:
            embed_model = os.environ.get("GEMINI_EMBED_MODEL", _DEFAULT_EMBED_MODEL)
            gen_model = os.environ.get("GEMINI_MODEL", _DEFAULT_GEN_MODEL)
            return cls(
                GeminiRetriever(documents, api_key=api_key, model=embed_model),
                GeminiAnswerer(api_key=api_key, model=gen_model),
                backend="gemini",
            )
        return cls(TfidfRetriever(documents), ExtractiveAnswerer(), backend="offline")

    def ask(self, question: str, *, k: int = 4) -> Answer:
        """Answer a question from retrieved sources, with citations."""
        hits = self._retriever.search(question, k)
        contexts = [doc for doc, _ in hits]
        answer_text = self._answerer.answer(question, contexts)
        citations = tuple(
            Citation(
                citation=doc.citation, source=doc.source, section=doc.section, score=round(score, 4)
            )
            for doc, score in hits
        )
        return Answer(
            question=question, answer=answer_text, citations=citations, backend=self._backend
        )

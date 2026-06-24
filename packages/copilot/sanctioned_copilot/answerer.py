"""Answer backends.

``ExtractiveAnswerer`` returns the retrieved passages directly — trivially
grounded, no model required. ``GeminiAnswerer`` synthesises a concise prose answer
*strictly from the retrieved context*, instructed to defer when the context does
not cover the question. Neither ever draws on the model's own world knowledge.
"""

from __future__ import annotations

from typing import Protocol

from sanctioned_copilot.corpus import Document

_SYSTEM = (
    "You are an operations assistant for a home-loan lender-matching system. "
    "Answer the question using ONLY the numbered context passages provided. "
    "Do not use any outside knowledge. If the passages do not contain the answer, "
    "reply exactly: 'I don't have that in the policy sources.' "
    "Be concise and refer to lenders by name."
)


class Answerer(Protocol):
    """Produces an answer string from a question and its retrieved context."""

    def answer(self, question: str, contexts: list[Document]) -> str: ...


class ExtractiveAnswerer:
    """Returns the retrieved passages verbatim — grounded with zero model calls."""

    def answer(self, question: str, contexts: list[Document]) -> str:
        if not contexts:
            return "I don't have that in the policy sources."
        return "\n\n".join(f"[{doc.citation}] {doc.text}" for doc in contexts[:2])


class GeminiAnswerer:
    """Synthesises a grounded answer from the context using Gemini.

    If the model is briefly unavailable (a transient 5xx), the answerer falls back
    to the extractive answer so the copilot still returns grounded, cited text
    rather than failing.
    """

    _ATTEMPTS = 3

    def __init__(self, *, api_key: str, model: str) -> None:
        from google import genai  # lazy import

        self._model = model
        self._client = genai.Client(api_key=api_key)
        self._fallback = ExtractiveAnswerer()

    def answer(self, question: str, contexts: list[Document]) -> str:
        if not contexts:
            return "I don't have that in the policy sources."
        passages = "\n".join(
            f"[{i + 1}] {doc.citation}: {doc.text}" for i, doc in enumerate(contexts)
        )
        prompt = f"{_SYSTEM}\n\nContext:\n{passages}\n\nQuestion: {question}\nAnswer:"
        for attempt in range(self._ATTEMPTS):
            try:
                response = self._client.models.generate_content(model=self._model, contents=prompt)
            except Exception:
                if attempt == self._ATTEMPTS - 1:
                    return self._fallback.answer(question, contexts)
                continue
            text = (response.text or "").strip()
            if text:
                return text
        return self._fallback.answer(question, contexts)

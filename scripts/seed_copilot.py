"""CLI: build the copilot and answer the seeded ops questions with citations.

Uses the Gemini backend when GEMINI_API_KEY is set, otherwise the offline
TF-IDF/extractive backend. Run:

    uv run python scripts/seed_copilot.py
"""

from __future__ import annotations

from sanctioned_copilot.copilot import Copilot

SEEDED_QUESTIONS = [
    "Which lenders accept self-employed borrowers with only two years of ITR?",
    "Which lender offers the lowest interest rate for a prime borrower?",
    "Do any lenders consider applicants with no credit history (a thin file)?",
    "What is the maximum loan-to-value on a property above 75 lakh?",
    "Which lenders fund under-construction properties, and at what LTV?",
]


def main() -> int:
    copilot = Copilot.build()
    print(f"Copilot backend: {copilot.backend}\n")
    for question in SEEDED_QUESTIONS:
        answer = copilot.ask(question)
        print(f"Q: {question}")
        print(f"A: {answer.answer}")
        print("   Sources: " + "; ".join(c.citation for c in answer.citations))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

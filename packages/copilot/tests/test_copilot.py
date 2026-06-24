"""Offline tests for the ops copilot.

These force the deterministic TF-IDF backend (no key, no network) and assert that
each of the five seeded ops questions retrieves the correct policy/section — the
Phase 4 DoD. The live Gemini path is exercised separately.
"""

from __future__ import annotations

import pytest
from sanctioned_copilot.copilot import Answer, Copilot


@pytest.fixture(scope="module")
def copilot() -> Copilot:
    return Copilot.build(prefer_live=False)


def _sections(answer: Answer) -> set[str]:
    return {c.section for c in answer.citations}


def _mentions(answer: Answer, *needles: str) -> bool:
    blob = " ".join(c.citation for c in answer.citations).lower()
    return any(n in blob for n in needles)


def test_backend_is_offline_and_cited(copilot: Copilot) -> None:
    answer = copilot.ask("What decides whether a borrower is approved?")
    assert answer.backend == "offline"
    assert len(answer.citations) >= 1


def test_self_employed_two_year_itr(copilot: Copilot) -> None:
    answer = copilot.ask("Which lenders accept self-employed borrowers with only two years of ITR?")
    assert "self_employed" in _sections(answer)
    assert _mentions(answer, "hfc", "nbfc")


def test_lowest_rate_for_prime(copilot: Copilot) -> None:
    answer = copilot.ask("Which lender offers the lowest interest rate for a prime borrower?")
    # The answer must be grounded in a rate/CIBIL source naming the cheapest lender.
    grounded = (
        any("cibil" in section for section in _sections(answer))
        or "8.10" in answer.answer
        or "public-sector" in answer.answer.lower()
    )
    assert grounded


def test_thin_file_acceptance(copilot: Copilot) -> None:
    answer = copilot.ask("Do any lenders consider applicants with no credit history?")
    assert "cibil" in _sections(answer) or _mentions(answer, "runbook")


def test_high_value_ltv(copilot: Copilot) -> None:
    answer = copilot.ask(
        "What is the maximum loan-to-value on a high-value property above 75 lakh?"
    )
    assert "ltv" in _sections(answer)


def test_under_construction(copilot: Copilot) -> None:
    answer = copilot.ask("Which lenders fund under-construction properties and at what LTV?")
    assert "property" in _sections(answer) or _mentions(answer, "runbook")


def test_all_five_seeded_questions_have_citations(copilot: Copilot) -> None:
    questions = [
        "Which lenders accept self-employed borrowers with only two years of ITR?",
        "Which lender offers the lowest interest rate for a prime borrower?",
        "Do any lenders consider applicants with no credit history?",
        "What is the maximum loan-to-value on a high-value property above 75 lakh?",
        "Which lenders fund under-construction properties and at what LTV?",
    ]
    for question in questions:
        answer = copilot.ask(question)
        assert answer.citations, f"no citations for: {question}"

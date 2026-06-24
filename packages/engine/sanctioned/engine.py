"""The matching orchestrator: one borrower against the whole lender panel.

Dispatches each policy to the right product flow, then ranks the results. The
engine itself holds no business rules — it composes the product/rule layers and
sorts. Determinism is guaranteed: the same inputs always produce identical,
identically-ordered output (the ``generated_at`` timestamp is the only injected
value, and can be supplied for reproducible snapshots).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sanctioned.products.new_loan import evaluate_new_loan
from sanctioned.registry import Registry
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import ProductType
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import EligibilityResult, MatchResult, MatchSummary

# Sorts rejected lenders (and missing rates) to the end deterministically.
_RATE_SENTINEL = Decimal("9999")


def evaluate_lender(profile: BorrowerProfile, policy: LenderPolicy) -> EligibilityResult:
    """Evaluate one policy against a borrower, dispatching on the requested product."""
    product = profile.loan_request.product_type
    if product is ProductType.NEW_HOME_LOAN:
        return evaluate_new_loan(profile, policy)
    # Balance transfer and top-up arrive in Phase 3.
    raise NotImplementedError(f"product {product.value} is not yet supported")


def _sort_key(result: EligibilityResult) -> tuple[int, Decimal, Decimal]:
    rate = result.indicative_rate_pct if result.indicative_rate_pct is not None else _RATE_SENTINEL
    return (0 if result.eligible else 1, -result.max_sanction, rate)


def _summarize(results: tuple[EligibilityResult, ...]) -> MatchSummary:
    eligible = [r for r in results if r.eligible]
    rates = [r.indicative_rate_pct for r in eligible if r.indicative_rate_pct is not None]
    sanctions = [r.max_sanction for r in results]
    top = results[0] if results and results[0].eligible else None
    return MatchSummary(
        eligible_count=len(eligible),
        best_rate=min(rates) if rates else None,
        max_sanction_overall=max(sanctions) if sanctions else Decimal(0),
        top_lender_id=top.lender_id if top is not None else None,
    )


def match(
    profile: BorrowerProfile,
    registry: Registry,
    *,
    generated_at: datetime | None = None,
) -> MatchResult:
    """Run a borrower against every policy in ``registry`` and rank the outcomes.

    Results are ordered eligible-first, then by descending max sanction, then by
    ascending indicative rate.
    """
    results = tuple(evaluate_lender(profile, policy) for policy in registry)
    ranked = tuple(sorted(results, key=_sort_key))
    return MatchResult(
        borrower=profile,
        generated_at=generated_at or datetime.now(UTC),
        results=ranked,
        summary=_summarize(ranked),
    )

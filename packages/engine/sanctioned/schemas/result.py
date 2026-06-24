"""The engine's explainable output.

A :class:`ReasonTrace` is emitted for *every* evaluated rule — passed or failed —
in evaluation order. The dashboard renders these verbatim; they are the
explainability deliverable, not a debugging aid. Results are immutable snapshots.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import Constraint, Decision

_FROZEN = ConfigDict(frozen=True)


class ReasonTrace(BaseModel):
    """One line of the audit trail for a single evaluated rule.

    ``value`` (the borrower's value) and ``threshold`` (the policy threshold) are
    always populated so the trace reads as a self-contained explanation.
    """

    model_config = _FROZEN

    code: str  # stable machine code, e.g. "CIBIL_FLOOR", "FOIR_CAP", "LTV_CAP"
    rule: str  # human-readable label
    passed: bool
    value: str  # the borrower's value, stringified
    threshold: str  # the policy threshold, stringified
    detail: str  # one-line explanation


class Bounds(BaseModel):
    """The four candidate ceilings; the smallest becomes the max sanction."""

    model_config = _FROZEN

    foir: Decimal
    ltv: Decimal
    multiplier: Decimal
    lender_cap: Decimal


class EligibilityResult(BaseModel):
    """The outcome of evaluating one lender's policy against one borrower."""

    model_config = _FROZEN

    lender_id: str
    lender_name: str
    decision: Decision
    eligible: bool
    max_sanction: Decimal
    binding_constraint: Constraint | None
    indicative_rate_pct: Decimal | None
    indicative_emi: Decimal | None
    bounds: Bounds
    effective_tenure_years: int
    reasons: tuple[ReasonTrace, ...]
    warnings: tuple[str, ...] = ()

    # Populated for balance-transfer and top-up products only.
    monthly_saving: Decimal | None = None
    net_benefit_note: str | None = None


class MatchSummary(BaseModel):
    """Roll-up across all lenders for quick scanning."""

    model_config = _FROZEN

    eligible_count: int = Field(ge=0)
    best_rate: Decimal | None
    max_sanction_overall: Decimal
    top_lender_id: str | None


class MatchResult(BaseModel):
    """The engine's full response: one borrower against the whole lender panel.

    ``results`` are sorted eligible-first, then by descending max sanction, then
    by ascending rate.
    """

    model_config = _FROZEN

    borrower: BorrowerProfile
    generated_at: datetime
    results: tuple[EligibilityResult, ...]
    summary: MatchSummary

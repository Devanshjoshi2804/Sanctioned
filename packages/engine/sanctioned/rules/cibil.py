"""CIBIL band selection: decision and indicative base rate (spec §5.5).

The applicant's score selects exactly one band (validated to be gap-free). A
band whose decision is REJECT — or a score for which no band matches, such as a
thin file at a lender that does not accept one — is a hard rejection. A REFER band
keeps the lender in play but flags manual review.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sanctioned.schemas.borrower import THIN_FILE_CIBIL, BorrowerProfile
from sanctioned.schemas.enums import Decision
from sanctioned.schemas.policy import CibilTier, LenderPolicy
from sanctioned.schemas.result import ReasonTrace


@dataclass(frozen=True)
class CibilOutcome:
    """Result of CIBIL evaluation, before any employer rate discount."""

    decision: Decision
    base_rate_pct: Decimal | None
    rejected: bool
    refer: bool
    trace: ReasonTrace


def select_tier(tiers: tuple[CibilTier, ...], score: int) -> CibilTier | None:
    """Return the band matching ``score`` (thin file = the ``-1`` band), or None."""
    for tier in tiers:
        if tier.min_score <= score <= tier.max_score:
            return tier
    return None


def evaluate_cibil(profile: BorrowerProfile, policy: LenderPolicy) -> CibilOutcome:
    """Pick the CIBIL band and derive the decision and base rate."""
    score = profile.applicant.cibil
    tier = select_tier(policy.cibil_tiers, score)
    score_label = "thin file" if score == THIN_FILE_CIBIL else str(score)

    if tier is None:
        # No band accepts this score (e.g. a thin file the lender won't fund).
        trace = ReasonTrace(
            code="CIBIL_FLOOR",
            rule="CIBIL score band",
            passed=False,
            value=score_label,
            threshold="no accepting band",
            detail=f"No CIBIL band covers {score_label}; the lender will not fund it",
        )
        return CibilOutcome(
            decision=Decision.REJECT, base_rate_pct=None, rejected=True, refer=False, trace=trace
        )

    rejected = tier.decision is Decision.REJECT
    refer = tier.decision is Decision.REFER
    band_label = (
        "thin file" if tier.min_score == THIN_FILE_CIBIL else f"{tier.min_score}-{tier.max_score}"
    )
    detail = f"Score {score_label} falls in band {band_label} -> {tier.decision.value}"
    trace = ReasonTrace(
        code="CIBIL_FLOOR",
        rule="CIBIL score band",
        passed=not rejected,
        value=score_label,
        threshold=f"band {band_label}",
        detail=detail,
    )
    return CibilOutcome(
        decision=tier.decision,
        base_rate_pct=tier.rate_pct,
        rejected=rejected,
        refer=refer,
        trace=trace,
    )

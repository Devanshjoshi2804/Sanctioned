"""Cross-field business-rule validation for lender policies (spec §6).

The Pydantic schema guarantees a policy is *structurally* sound (right types,
non-negative amounts, individual ranges). This module asserts the *relational*
invariants a schema cannot express — and, critically, fails loud with the
offending ``lender_id`` and field so a bad rate-card edit is caught at load time
with an actionable message rather than producing silently wrong matches.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from itertools import pairwise

from sanctioned.schemas.enums import Decision
from sanctioned.schemas.policy import LenderPolicy

# Signature of the failure callback threaded through the per-section checks. It
# always raises, so control never returns to the caller.
_Fail = Callable[[str, str], None]

# The hard ceiling for any FOIR cap. Lenders may stretch toward this with employer
# bonuses at match time, but a *policy* band above it is almost always a data error.
FOIR_CAP_CEILING_PCT = Decimal(70)

# The full CIBIL scoring range that bands must cover contiguously.
CIBIL_MIN_SCORE = 300
CIBIL_MAX_SCORE = 900
THIN_FILE_SENTINEL = -1


class PolicyValidationError(ValueError):
    """Raised when a lender policy violates a business invariant.

    Carries the ``lender_id`` and ``field`` so callers (CI, the registry loader)
    can point an operator straight at the offending YAML.
    """

    def __init__(self, lender_id: str, field: str, message: str) -> None:
        self.lender_id = lender_id
        self.field = field
        self.message = message
        super().__init__(f"[{lender_id}] {field}: {message}")


def validate_policy(policy: LenderPolicy) -> None:
    """Assert every business invariant for ``policy``; raise on the first breach."""

    def fail(field: str, message: str) -> None:
        raise PolicyValidationError(policy.lender_id, field, message)

    _validate_provenance(policy, fail)
    _validate_age(policy, fail)
    _validate_limits(policy, fail)
    _validate_foir(policy, fail)
    _validate_ltv_bands(policy, fail)
    _validate_cibil_tiers(policy, fail)


def _validate_provenance(policy: LenderPolicy, fail: _Fail) -> None:
    if not policy.source.strip():
        fail("source", "source must be a non-empty provenance reference")
    if not policy.disclaimer.strip():
        fail("disclaimer", "disclaimer must be a non-empty 'indicative' notice")


def _validate_age(policy: LenderPolicy, fail: _Fail) -> None:
    for class_name, block in (
        ("salaried", policy.age.salaried),
        ("self_employed", policy.age.self_employed),
    ):
        if block.max_at_maturity <= block.min_entry:
            fail(
                f"age.{class_name}",
                f"max_at_maturity ({block.max_at_maturity}) must exceed "
                f"min_entry ({block.min_entry})",
            )


def _validate_limits(policy: LenderPolicy, fail: _Fail) -> None:
    if policy.limits.min_loan >= policy.limits.max_loan:
        fail(
            "limits",
            f"min_loan ({policy.limits.min_loan}) must be below "
            f"max_loan ({policy.limits.max_loan})",
        )


def _validate_foir(policy: LenderPolicy, fail: _Fail) -> None:
    for class_name, bands in (
        ("salaried", policy.foir.salaried),
        ("self_employed", policy.foir.self_employed),
    ):
        for band in bands:
            if band.cap_pct > FOIR_CAP_CEILING_PCT:
                fail(
                    f"foir.{class_name}",
                    f"cap_pct ({band.cap_pct}) exceeds the {FOIR_CAP_CEILING_PCT}% ceiling",
                )


def _validate_ltv_bands(policy: LenderPolicy, fail: _Fail) -> None:
    bands = policy.ltv_bands
    if not bands:
        fail("ltv_bands", "at least one LTV band is required")
        return

    # The open-ended (catch-all) band may appear only once, and only last.
    for index, band in enumerate(bands):
        is_last = index == len(bands) - 1
        if band.up_to_amount is None and not is_last:
            fail("ltv_bands", "the open-ended band (up_to_amount: null) must be last")

    # Amount ceilings strictly ascending; max LTV non-increasing as amount grows
    # (a larger loan never earns a more generous LTV).
    previous_amount: Decimal | None = None
    previous_ltv: Decimal | None = None
    for band in bands:
        if (
            previous_amount is not None
            and band.up_to_amount is not None
            and band.up_to_amount <= previous_amount
        ):
            fail("ltv_bands", "up_to_amount ceilings must be strictly ascending")
        if previous_ltv is not None and band.max_ltv_pct > previous_ltv:
            fail(
                "ltv_bands",
                f"max_ltv_pct must be non-increasing across bands "
                f"({band.max_ltv_pct} > {previous_ltv})",
            )
        previous_amount = band.up_to_amount if band.up_to_amount is not None else previous_amount
        previous_ltv = band.max_ltv_pct


def _validate_cibil_tiers(policy: LenderPolicy, fail: _Fail) -> None:
    scoring = [
        tier
        for tier in policy.cibil_tiers
        if not (tier.min_score == THIN_FILE_SENTINEL and tier.max_score == THIN_FILE_SENTINEL)
    ]
    if not scoring:
        fail("cibil_tiers", "at least one scoring band (300..900) is required")
        return

    # Rates must be present wherever a decision can approve/refer.
    for tier in policy.cibil_tiers:
        if tier.decision is not Decision.REJECT and tier.rate_pct is None:
            fail(
                "cibil_tiers",
                f"rate_pct is required for non-REJECT band {tier.min_score}..{tier.max_score}",
            )

    for tier in scoring:
        if tier.min_score > tier.max_score:
            fail(
                "cibil_tiers",
                f"band has min_score ({tier.min_score}) above max_score ({tier.max_score})",
            )

    ordered = sorted(scoring, key=lambda tier: tier.min_score)
    if ordered[0].min_score != CIBIL_MIN_SCORE or ordered[-1].max_score != CIBIL_MAX_SCORE:
        fail(
            "cibil_tiers",
            f"scoring bands must cover {CIBIL_MIN_SCORE}..{CIBIL_MAX_SCORE} exactly",
        )
    for previous, current in pairwise(ordered):
        if current.min_score != previous.max_score + 1:
            fail(
                "cibil_tiers",
                f"gap or overlap between {previous.max_score} and {current.min_score}",
            )


__all__ = ["PolicyValidationError", "validate_policy"]

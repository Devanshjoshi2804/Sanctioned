"""The loan-to-value sanction bound (spec §5.4.2).

LTV bands are keyed off the *loan amount*, which is itself the thing we are
solving for. We resolve the self-consistent band by walking the bands from the
smallest amount ceiling upward and taking the first whose implied loan
(``value x ltv``) fits within that band's ceiling. Property-type and product
overrides then cap the resulting LTV downward.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sanctioned.rules._support import HUNDRED, percent, rupees
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import ReasonTrace


@dataclass(frozen=True)
class LtvOutcome:
    """Result of the LTV bound calculation."""

    bound: Decimal
    effective_ltv_pct: Decimal
    trace: ReasonTrace


def _self_consistent_band_ltv(policy: LenderPolicy, property_value: Decimal) -> Decimal:
    """Pick the LTV whose implied loan amount falls within its own band ceiling."""
    for band in policy.ltv_bands:
        implied_loan = property_value * band.max_ltv_pct / HUNDRED
        if band.up_to_amount is None or implied_loan <= band.up_to_amount:
            return band.max_ltv_pct
    return policy.ltv_bands[-1].max_ltv_pct


def ltv_bound(
    *,
    property_value: Decimal,
    policy: LenderPolicy,
    ltv_override_pct: Decimal | None = None,
    product_max_ltv_pct: Decimal | None = None,
) -> LtvOutcome:
    """Return the LTV-capped loan ceiling, applying any overrides."""
    base_ltv = _self_consistent_band_ltv(policy, property_value)
    caps = [base_ltv]
    if ltv_override_pct is not None:
        caps.append(ltv_override_pct)
    if product_max_ltv_pct is not None:
        caps.append(product_max_ltv_pct)
    effective_ltv = min(caps)

    bound = property_value * effective_ltv / HUNDRED
    capped_note = "" if effective_ltv == base_ltv else f" (capped from {percent(base_ltv)})"
    trace = ReasonTrace(
        code="LTV_CAP",
        rule="Loan-to-value ratio",
        passed=True,
        value=rupees(bound),
        threshold=f"{percent(effective_ltv)} of {rupees(property_value)}",
        detail=f"LTV caps the loan at {rupees(bound)} ({percent(effective_ltv)}{capped_note})",
    )
    return LtvOutcome(bound=bound, effective_ltv_pct=effective_ltv, trace=trace)

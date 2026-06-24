"""The FOIR (fixed-obligations-to-income) sanction bound (spec §5.4.1).

The lender allows a capped share of assessed income toward all EMIs. After
subtracting existing obligations, the remaining headroom is the EMI the new loan
may carry; the present value of that EMI stream is the FOIR bound. An employer
bonus may lift the cap, but never past a sane total ceiling. No headroom is a hard
rejection.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sanctioned.emi import max_principal
from sanctioned.rules._support import HUNDRED, percent, rupees
from sanctioned.schemas.policy import FoirBand, LenderPolicy
from sanctioned.schemas.result import ReasonTrace

# The absolute upper bound on a FOIR cap once employer bonuses are added (§5.4.1).
FOIR_TOTAL_CEILING_PCT = Decimal(65)


@dataclass(frozen=True)
class FoirOutcome:
    """Result of the FOIR bound calculation."""

    bound: Decimal
    available_emi: Decimal
    effective_cap_pct: Decimal
    rejected: bool
    traces: tuple[ReasonTrace, ...]


def select_cap_pct(bands: tuple[FoirBand, ...], assessed_income: Decimal) -> Decimal:
    """First band whose income ceiling covers the assessed income (null = catch-all)."""
    for band in bands:
        if band.up_to_nmi is None or assessed_income <= band.up_to_nmi:
            return band.cap_pct
    return bands[-1].cap_pct


def foir_bound(
    *,
    assessed_income: Decimal,
    existing_obligations: Decimal,
    policy: LenderPolicy,
    is_self_employed: bool,
    foir_bonus_pct: Decimal,
    rate_pct: Decimal,
    tenure_months: int,
) -> FoirOutcome:
    """Return the FOIR-capped loan ceiling (or a no-headroom rejection)."""
    bands = policy.foir.self_employed if is_self_employed else policy.foir.salaried
    base_cap = select_cap_pct(bands, assessed_income)
    effective_cap = min(base_cap + foir_bonus_pct, FOIR_TOTAL_CEILING_PCT)

    available_emi = assessed_income * effective_cap / HUNDRED - existing_obligations
    cap_note = "" if effective_cap == base_cap else " (incl. employer bonus, capped)"
    cap_trace = ReasonTrace(
        code="FOIR_CAP",
        rule="FOIR cap",
        passed=available_emi > 0,
        value=f"EMI headroom {rupees(available_emi)}",
        threshold=f"{percent(effective_cap)} of {rupees(assessed_income)}{cap_note}",
        detail=(
            f"{percent(effective_cap)} FOIR less {rupees(existing_obligations)} obligations "
            f"leaves {rupees(available_emi)} of EMI headroom"
        ),
    )

    if available_emi <= 0:
        no_headroom = ReasonTrace(
            code="FOIR_NO_HEADROOM",
            rule="FOIR headroom",
            passed=False,
            value=rupees(available_emi),
            threshold="> ₹0",
            detail="Existing obligations consume the entire FOIR allowance",
        )
        return FoirOutcome(
            bound=Decimal(0),
            available_emi=available_emi,
            effective_cap_pct=effective_cap,
            rejected=True,
            traces=(cap_trace, no_headroom),
        )

    bound = max_principal(available_emi, rate_pct, tenure_months)
    return FoirOutcome(
        bound=bound,
        available_emi=available_emi,
        effective_cap_pct=effective_cap,
        rejected=False,
        traces=(cap_trace,),
    )

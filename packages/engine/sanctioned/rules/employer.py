"""Employer-category perks: FOIR bonus and rate discount (spec §5.4, §5.5).

Premier employer categories may earn a small FOIR uplift and a rate discount.
A borrower whose category has no configured perk simply gets none.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import ReasonTrace


@dataclass(frozen=True)
class EmployerPerks:
    """The FOIR bonus and rate discount earned by the applicant's employer category."""

    foir_bonus_pct: Decimal
    rate_discount_bps: int
    trace: ReasonTrace | None  # None when no perk applies (nothing to explain)


def resolve_employer_perks(profile: BorrowerProfile, policy: LenderPolicy) -> EmployerPerks:
    """Look up the perk for the applicant's employer category, if any."""
    category = profile.applicant.employer_category
    perk = next((p for p in policy.employer_category_perks if p.category is category), None)
    if perk is None:
        return EmployerPerks(foir_bonus_pct=Decimal(0), rate_discount_bps=0, trace=None)

    trace = ReasonTrace(
        code="EMPLOYER_PERK",
        rule="Employer category perk",
        passed=True,
        value=category.value,
        threshold=f"+{perk.foir_bonus_pct}% FOIR, -{perk.rate_discount_bps}bps",
        detail=(
            f"Employer category {category.value} grants a "
            f"{perk.foir_bonus_pct}% FOIR bonus and {perk.rate_discount_bps}bps rate discount"
        ),
    )
    return EmployerPerks(
        foir_bonus_pct=perk.foir_bonus_pct,
        rate_discount_bps=perk.rate_discount_bps,
        trace=trace,
    )

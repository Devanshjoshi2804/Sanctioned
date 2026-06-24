"""The NMI-multiplier sanction bound (spec §5.4.3).

The simplest of the three bounds: the loan may not exceed a fixed multiple of
assessed monthly income.
"""

from __future__ import annotations

from decimal import Decimal

from sanctioned.rules._support import rupees
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import ReasonTrace


def multiplier_bound(assessed_income: Decimal, policy: LenderPolicy) -> tuple[Decimal, ReasonTrace]:
    """Return the loan ceiling implied by the NMI multiplier, with its trace."""
    multiplier = policy.nmi_multiplier.max
    bound = multiplier * assessed_income
    trace = ReasonTrace(
        code="MULTIPLIER_CAP",
        rule="Net-monthly-income multiplier",
        passed=True,
        value=rupees(bound),
        threshold=f"{multiplier}x {rupees(assessed_income)}",
        detail=f"Income multiple caps the loan at {rupees(bound)} ({multiplier}x assessed income)",
    )
    return bound, trace

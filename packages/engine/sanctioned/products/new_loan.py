"""NEW_HOME_LOAN evaluation (spec §5.6).

Runs the shared qualifying gates, then sizes the loan as the smallest of the three
bounds (FOIR, LTV, NMI multiplier) against the lender cap, and resolves the final
decision. Every evaluated rule contributes a reason trace, in evaluation order.
"""

from __future__ import annotations

from decimal import Decimal

from sanctioned.emi import round_rupees
from sanctioned.products._common import (
    ZERO_BOUNDS,
    Qualification,
    build_result,
    qualify,
    smallest_bound,
)
from sanctioned.rules.foir import foir_bound
from sanctioned.rules.ltv import ltv_bound
from sanctioned.rules.multiplier import multiplier_bound
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import Decision
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import Bounds, EligibilityResult, ReasonTrace


def evaluate_new_loan(profile: BorrowerProfile, policy: LenderPolicy) -> EligibilityResult:
    """Evaluate a NEW_HOME_LOAN request for one borrower against one policy."""
    qual = qualify(profile, policy)
    if qual.hard_failed or qual.rate_pct is None:
        return build_result(
            policy,
            decision=Decision.REJECT,
            max_sanction=Decimal(0),
            binding=None,
            rate_pct=None,
            tenure_years=max(qual.tenure_years, 0),
            bounds=ZERO_BOUNDS,
            reasons=qual.reasons,
        )
    return _size_and_decide(profile, policy, qual)


def _size_and_decide(
    profile: BorrowerProfile, policy: LenderPolicy, qual: Qualification
) -> EligibilityResult:
    assert qual.rate_pct is not None  # guaranteed by the caller's guard
    reasons = qual.reasons
    tenure_months = qual.tenure_years * 12

    foir = foir_bound(
        assessed_income=qual.assessed_income,
        existing_obligations=profile.existing_monthly_obligations,
        policy=policy,
        is_self_employed=profile.applicant.employment_type.is_self_employed,
        foir_bonus_pct=qual.foir_bonus_pct,
        rate_pct=qual.rate_pct,
        tenure_months=tenure_months,
    )
    reasons.extend(foir.traces)

    ltv = ltv_bound(
        property_value=profile.property.value,
        policy=policy,
        ltv_override_pct=qual.property_ltv_override_pct,
    )
    reasons.append(ltv.trace)

    multiplier_value, multiplier_trace = multiplier_bound(qual.assessed_income, policy)
    reasons.append(multiplier_trace)

    bounds = Bounds(
        foir=round_rupees(foir.bound),
        ltv=round_rupees(ltv.bound),
        multiplier=round_rupees(multiplier_value),
        lender_cap=round_rupees(policy.limits.max_loan),
    )

    if foir.rejected:
        return build_result(
            policy,
            decision=Decision.REJECT,
            max_sanction=Decimal(0),
            binding=None,
            rate_pct=qual.rate_pct,
            tenure_years=qual.tenure_years,
            bounds=bounds,
            reasons=reasons,
        )

    binding, sanction_raw = smallest_bound(
        foir.bound, ltv.bound, multiplier_value, policy.limits.max_loan
    )
    max_sanction = round_rupees(max(sanction_raw, Decimal(0)))

    if max_sanction < policy.limits.min_loan:
        reasons.append(
            ReasonTrace(
                code="BELOW_MIN_LOAN",
                rule="Minimum loan size",
                passed=False,
                value=str(max_sanction),
                threshold=str(round_rupees(policy.limits.min_loan)),
                detail="Eligible amount is below the lender's minimum loan size",
            )
        )
        return build_result(
            policy,
            decision=Decision.REJECT,
            max_sanction=Decimal(0),
            binding=binding,
            rate_pct=qual.rate_pct,
            tenure_years=qual.tenure_years,
            bounds=bounds,
            reasons=reasons,
        )

    decision = Decision.REFER if qual.refer else Decision.APPROVE
    return build_result(
        policy,
        decision=decision,
        max_sanction=max_sanction,
        binding=binding,
        rate_pct=qual.rate_pct,
        tenure_years=qual.tenure_years,
        bounds=bounds,
        reasons=reasons,
    )

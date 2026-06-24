"""TOP_UP evaluation (spec §5.6).

A top-up adds new borrowing on top of an existing loan. Eligibility is assessed on
the *combined* exposure: the combined amount must satisfy a dedicated combined-LTV
cap (``TOPUP_LTV``) and the FOIR headroom must service the combined EMI. The
reported sanction is the additional amount available beyond the outstanding.
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
from sanctioned.rules._support import HUNDRED, rupees
from sanctioned.rules.foir import foir_bound
from sanctioned.rules.ltv import ltv_bound
from sanctioned.rules.multiplier import multiplier_bound
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import Decision, ProductType
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import Bounds, EligibilityResult, ReasonTrace


def evaluate_top_up(profile: BorrowerProfile, policy: LenderPolicy) -> EligibilityResult:
    """Evaluate a TOP_UP request for one borrower against one policy."""
    outstanding = profile.loan_request.existing_loan_outstanding
    requested = profile.loan_request.requested_amount
    combined = outstanding + (requested or Decimal(0))
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

    combined_ltv_cap = _combined_ltv_cap(profile, policy, qual.property_ltv_override_pct)
    reasons.append(_topup_ltv_trace(combined, combined_ltv_cap))

    multiplier_value, multiplier_trace = multiplier_bound(qual.assessed_income, policy)
    reasons.append(multiplier_trace)

    bounds = Bounds(
        foir=round_rupees(foir.bound),
        ltv=round_rupees(combined_ltv_cap),
        multiplier=round_rupees(multiplier_value),
        lender_cap=round_rupees(policy.limits.max_loan),
    )

    if foir.rejected:
        return _reject(policy, qual, bounds, reasons)

    binding, combined_cap = smallest_bound(
        foir.bound, combined_ltv_cap, multiplier_value, policy.limits.max_loan
    )
    available = round_rupees(max(combined_cap - outstanding, Decimal(0)))

    if available <= 0:
        return _reject(policy, qual, bounds, reasons)

    warnings: tuple[str, ...] = ()
    if requested is not None and available < requested:
        decision = Decision.REFER
        sanction = available
        warnings = (
            f"Only {rupees(available)} of top-up is available against the "
            f"{rupees(requested)} requested.",
        )
    else:
        decision = Decision.REFER if qual.refer else Decision.APPROVE
        sanction = requested if requested is not None else available

    return build_result(
        policy,
        decision=decision,
        max_sanction=sanction,
        binding=binding,
        rate_pct=qual.rate_pct,
        tenure_years=qual.tenure_years,
        bounds=bounds,
        reasons=reasons,
        warnings=warnings,
    )


def _combined_ltv_cap(
    profile: BorrowerProfile, policy: LenderPolicy, property_override_pct: Decimal | None
) -> Decimal:
    override = policy.product_overrides.get(ProductType.TOP_UP)
    if override is not None and override.combined_max_ltv_pct is not None:
        return profile.property.value * override.combined_max_ltv_pct / HUNDRED
    # Fall back to the base LTV bound when no combined override is configured.
    return ltv_bound(
        property_value=profile.property.value,
        policy=policy,
        ltv_override_pct=property_override_pct,
    ).bound


def _topup_ltv_trace(combined: Decimal, cap: Decimal) -> ReasonTrace:
    passed = combined <= cap
    return ReasonTrace(
        code="TOPUP_LTV",
        rule="Combined LTV (top-up)",
        passed=passed,
        value=rupees(combined),
        threshold=rupees(cap),
        detail=(
            f"Combined exposure {rupees(combined)} "
            f"{'within' if passed else 'exceeds'} the combined-LTV cap {rupees(cap)}"
        ),
    )


def _reject(
    policy: LenderPolicy,
    qual: Qualification,
    bounds: Bounds,
    reasons: list[ReasonTrace],
) -> EligibilityResult:
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

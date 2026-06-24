"""BALANCE_TRANSFER evaluation (spec §5.6).

A balance transfer re-underwrites the borrower's *outstanding* loan at this
lender's terms. We size the lender's capacity exactly as for a new loan (applying
the BT-specific LTV override), then check whether that capacity covers the
outstanding and quantify the indicative monthly saving from the rate change.
Processing/foreclosure friction is surfaced as a note, never a hard rejection.
"""

from __future__ import annotations

from decimal import Decimal

from sanctioned.emi import emi, round_rupees
from sanctioned.products._common import (
    ZERO_BOUNDS,
    build_result,
    qualify,
    smallest_bound,
)
from sanctioned.rules.foir import foir_bound
from sanctioned.rules.ltv import ltv_bound
from sanctioned.rules.multiplier import multiplier_bound
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import Decision, ProductType
from sanctioned.schemas.policy import LenderPolicy, ProductOverride
from sanctioned.schemas.result import Bounds, EligibilityResult, ReasonTrace


def evaluate_balance_transfer(profile: BorrowerProfile, policy: LenderPolicy) -> EligibilityResult:
    """Evaluate a BALANCE_TRANSFER request for one borrower against one policy."""
    outstanding = profile.loan_request.existing_loan_outstanding
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
    override = policy.product_overrides.get(ProductType.BALANCE_TRANSFER)
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
        product_max_ltv_pct=override.max_ltv_pct if override else None,
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

    binding, capacity_raw = smallest_bound(
        foir.bound, ltv.bound, multiplier_value, policy.limits.max_loan
    )
    capacity = round_rupees(max(capacity_raw, Decimal(0)))

    reasons.append(_outstanding_trace(outstanding, capacity, policy))
    if (
        outstanding <= 0
        or outstanding < policy.limits.min_loan
        or capacity < policy.limits.min_loan
    ):
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

    transfer_amount = min(capacity, outstanding)
    warnings = _seasoning_warnings(override)
    decision = Decision.REFER if qual.refer else Decision.APPROVE
    if capacity < outstanding:
        decision = Decision.REFER
        warnings = (
            *warnings,
            f"Lender capacity ₹{capacity:,.0f} covers only part of the "
            f"₹{outstanding:,.0f} outstanding.",
        )

    monthly_saving, note = _savings(profile, qual.rate_pct, outstanding, tenure_months)

    return build_result(
        policy,
        decision=decision,
        max_sanction=transfer_amount,
        binding=binding,
        rate_pct=qual.rate_pct,
        tenure_years=qual.tenure_years,
        bounds=bounds,
        reasons=reasons,
        warnings=warnings,
        monthly_saving=monthly_saving,
        net_benefit_note=note,
    )


def _outstanding_trace(
    outstanding: Decimal, capacity: Decimal, policy: LenderPolicy
) -> ReasonTrace:
    covers = outstanding <= capacity and outstanding >= policy.limits.min_loan and outstanding > 0
    return ReasonTrace(
        code="BT_CAPACITY",
        rule="Balance-transfer capacity",
        passed=covers,
        value=f"₹{outstanding:,.0f} outstanding",
        threshold=f"capacity ₹{capacity:,.0f}",
        detail=(f"Lender can fund ₹{capacity:,.0f}; outstanding is ₹{outstanding:,.0f}"),
    )


def _seasoning_warnings(override: ProductOverride | None) -> tuple[str, ...]:
    months = override.min_seasoning_months if override else None
    if months:
        return (
            f"Requires at least {months} months of seasoning on the existing loan "
            f"(not verified from the profile).",
        )
    return ()


def _savings(
    profile: BorrowerProfile,
    new_rate_pct: Decimal,
    outstanding: Decimal,
    tenure_months: int,
) -> tuple[Decimal | None, str | None]:
    existing_rate = profile.loan_request.existing_rate_pct
    if not existing_rate or outstanding <= 0 or tenure_months <= 0:
        return None, None
    old_emi = emi(outstanding, existing_rate, tenure_months)
    new_emi = emi(outstanding, new_rate_pct, tenure_months)
    saving = round_rupees(old_emi - new_emi)
    note = (
        "Indicative monthly saving from the rate change; weigh against processing "
        "and foreclosure charges before transferring."
    )
    return saving, note

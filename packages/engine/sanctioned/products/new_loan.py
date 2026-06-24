"""NEW_HOME_LOAN evaluation: compose the rule layer into one result (spec §5.6).

The flow is: run the qualifying gates (property, self-employed, income, CIBIL,
age/tenure); if any hard rule fails, reject with the trace explaining why.
Otherwise derive the indicative rate, compute the three sanction bounds, take the
smallest as the max sanction, and resolve the final decision. Every evaluated rule
contributes a reason trace, in evaluation order.
"""

from __future__ import annotations

from decimal import Decimal

from sanctioned.emi import emi, round_rupees
from sanctioned.rules.age_tenure import effective_tenure
from sanctioned.rules.cibil import evaluate_cibil
from sanctioned.rules.employer import resolve_employer_perks
from sanctioned.rules.foir import foir_bound
from sanctioned.rules.income import assessed_income, check_min_income, youngest_owner_age
from sanctioned.rules.ltv import ltv_bound
from sanctioned.rules.multiplier import multiplier_bound
from sanctioned.rules.property_ import evaluate_property
from sanctioned.rules.self_employed import evaluate_self_employed
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import Constraint, Decision
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import Bounds, EligibilityResult, ReasonTrace

_BPS_PER_PERCENT = Decimal(100)
_ZERO_BOUNDS = Bounds(foir=Decimal(0), ltv=Decimal(0), multiplier=Decimal(0), lender_cap=Decimal(0))


def evaluate_new_loan(profile: BorrowerProfile, policy: LenderPolicy) -> EligibilityResult:
    """Evaluate a NEW_HOME_LOAN request for one borrower against one policy."""
    reasons: list[ReasonTrace] = []
    hard_failed = False

    # --- Qualifying gates (evaluation order matters for the trace) ---
    prop = evaluate_property(profile, policy)
    reasons.append(prop.trace)
    hard_failed |= not prop.allowed

    se = evaluate_self_employed(profile, policy)
    reasons.extend(se.traces)
    hard_failed |= se.rejected

    min_income = check_min_income(profile, policy)
    reasons.append(min_income)
    hard_failed |= not min_income.passed

    cibil = evaluate_cibil(profile, policy)
    reasons.append(cibil.trace)
    hard_failed |= cibil.rejected

    perks = resolve_employer_perks(profile, policy)
    if perks.trace is not None:
        reasons.append(perks.trace)

    youngest_age = youngest_owner_age(profile)
    tenure = effective_tenure(
        profile,
        policy,
        youngest_age=youngest_age,
        property_tenure_override=prop.tenure_override_years,
    )
    reasons.append(tenure.trace)
    hard_failed |= tenure.rejected

    # A failed gate means we cannot meaningfully size the loan (e.g. no rate from a
    # rejected CIBIL band). Reject now with the traces gathered so far.
    if hard_failed or cibil.base_rate_pct is None:
        return _rejected(profile, policy, tenure.effective_years, reasons)

    # --- Sizing: indicative rate, then the three bounds ---
    rate_pct = max(
        cibil.base_rate_pct - Decimal(perks.rate_discount_bps) / _BPS_PER_PERCENT, Decimal(0)
    )
    tenure_months = tenure.effective_years * 12
    assessed = assessed_income(profile, policy)

    foir = foir_bound(
        assessed_income=assessed,
        existing_obligations=profile.existing_monthly_obligations,
        policy=policy,
        is_self_employed=profile.applicant.employment_type.is_self_employed,
        foir_bonus_pct=perks.foir_bonus_pct,
        rate_pct=rate_pct,
        tenure_months=tenure_months,
    )
    reasons.extend(foir.traces)

    ltv = ltv_bound(
        property_value=profile.property.value,
        policy=policy,
        ltv_override_pct=prop.ltv_override_pct,
    )
    reasons.append(ltv.trace)

    multiplier_value, multiplier_trace = multiplier_bound(assessed, policy)
    reasons.append(multiplier_trace)

    bounds = Bounds(
        foir=round_rupees(foir.bound),
        ltv=round_rupees(ltv.bound),
        multiplier=round_rupees(multiplier_value),
        lender_cap=round_rupees(policy.limits.max_loan),
    )

    if foir.rejected:
        return _build_result(
            profile,
            policy,
            decision=Decision.REJECT,
            max_sanction=Decimal(0),
            binding=None,
            rate_pct=rate_pct,
            tenure_years=tenure.effective_years,
            bounds=bounds,
            reasons=reasons,
        )

    binding, sanction_raw = _smallest_bound(foir.bound, ltv.bound, multiplier_value, policy)
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
        return _build_result(
            profile,
            policy,
            decision=Decision.REJECT,
            max_sanction=Decimal(0),
            binding=binding,
            rate_pct=rate_pct,
            tenure_years=tenure.effective_years,
            bounds=bounds,
            reasons=reasons,
        )

    decision = Decision.REFER if cibil.refer else Decision.APPROVE
    return _build_result(
        profile,
        policy,
        decision=decision,
        max_sanction=max_sanction,
        binding=binding,
        rate_pct=rate_pct,
        tenure_years=tenure.effective_years,
        bounds=bounds,
        reasons=reasons,
    )


def _smallest_bound(
    foir: Decimal, ltv: Decimal, multiplier: Decimal, policy: LenderPolicy
) -> tuple[Constraint, Decimal]:
    """Return the binding constraint and its value (the minimum of the four bounds)."""
    candidates = (
        (Constraint.FOIR, foir),
        (Constraint.LTV, ltv),
        (Constraint.NMI_MULTIPLIER, multiplier),
        (Constraint.LENDER_MAX_CAP, policy.limits.max_loan),
    )
    return min(candidates, key=lambda pair: pair[1])


def _rejected(
    profile: BorrowerProfile,
    policy: LenderPolicy,
    tenure_years: int,
    reasons: list[ReasonTrace],
) -> EligibilityResult:
    """Build a rejection result for a failed qualifying gate (no sizing performed)."""
    return _build_result(
        profile,
        policy,
        decision=Decision.REJECT,
        max_sanction=Decimal(0),
        binding=None,
        rate_pct=None,
        tenure_years=max(tenure_years, 0),
        bounds=_ZERO_BOUNDS,
        reasons=reasons,
    )


def _build_result(
    profile: BorrowerProfile,
    policy: LenderPolicy,
    *,
    decision: Decision,
    max_sanction: Decimal,
    binding: Constraint | None,
    rate_pct: Decimal | None,
    tenure_years: int,
    bounds: Bounds,
    reasons: list[ReasonTrace],
) -> EligibilityResult:
    """Assemble the final EligibilityResult, computing the indicative EMI."""
    eligible = decision is not Decision.REJECT
    indicative_emi: Decimal | None = None
    if eligible and rate_pct is not None and max_sanction > 0 and tenure_years > 0:
        indicative_emi = round_rupees(emi(max_sanction, rate_pct, tenure_years * 12))

    return EligibilityResult(
        lender_id=policy.lender_id,
        lender_name=policy.lender_name,
        decision=decision,
        eligible=eligible,
        max_sanction=max_sanction,
        binding_constraint=binding if eligible else None,
        indicative_rate_pct=rate_pct if eligible else None,
        indicative_emi=indicative_emi,
        bounds=bounds,
        effective_tenure_years=tenure_years,
        reasons=tuple(reasons),
    )

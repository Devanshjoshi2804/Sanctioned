"""Shared product machinery: qualification gates and result assembly.

All three products (new loan, balance transfer, top-up) run the same qualifying
gates, derive the same indicative rate, and assemble results the same way. That
shared logic lives here so each product module only expresses what is genuinely
product-specific (which bounds bind, and any savings/benefit notes).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sanctioned.emi import emi, round_rupees
from sanctioned.rules.age_tenure import effective_tenure
from sanctioned.rules.cibil import evaluate_cibil
from sanctioned.rules.employer import resolve_employer_perks
from sanctioned.rules.income import assessed_income, check_min_income, youngest_owner_age
from sanctioned.rules.property_ import evaluate_property
from sanctioned.rules.self_employed import evaluate_self_employed
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import Constraint, Decision
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import Bounds, EligibilityResult, ReasonTrace

_BPS_PER_PERCENT = Decimal(100)

ZERO_BOUNDS = Bounds(foir=Decimal(0), ltv=Decimal(0), multiplier=Decimal(0), lender_cap=Decimal(0))


@dataclass(frozen=True)
class Qualification:
    """The product-independent outcome of the qualifying gates."""

    reasons: list[ReasonTrace]
    hard_failed: bool
    refer: bool
    rate_pct: Decimal | None
    assessed_income: Decimal
    foir_bonus_pct: Decimal
    tenure_years: int
    property_ltv_override_pct: Decimal | None


def qualify(profile: BorrowerProfile, policy: LenderPolicy) -> Qualification:
    """Run the qualifying gates common to every product, in evaluation order."""
    reasons: list[ReasonTrace] = []
    hard_failed = False

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

    tenure = effective_tenure(
        profile,
        policy,
        youngest_age=youngest_owner_age(profile),
        property_tenure_override=prop.tenure_override_years,
    )
    reasons.append(tenure.trace)
    hard_failed |= tenure.rejected

    rate_pct: Decimal | None = None
    if cibil.base_rate_pct is not None:
        rate_pct = max(
            cibil.base_rate_pct - Decimal(perks.rate_discount_bps) / _BPS_PER_PERCENT, Decimal(0)
        )

    return Qualification(
        reasons=reasons,
        hard_failed=hard_failed or rate_pct is None,
        refer=cibil.refer,
        rate_pct=rate_pct,
        assessed_income=assessed_income(profile, policy),
        foir_bonus_pct=perks.foir_bonus_pct,
        tenure_years=tenure.effective_years,
        property_ltv_override_pct=prop.ltv_override_pct,
    )


def smallest_bound(
    foir: Decimal, ltv: Decimal, multiplier: Decimal, lender_cap: Decimal
) -> tuple[Constraint, Decimal]:
    """Return the binding constraint and its value (the minimum of the four bounds)."""
    candidates = (
        (Constraint.FOIR, foir),
        (Constraint.LTV, ltv),
        (Constraint.NMI_MULTIPLIER, multiplier),
        (Constraint.LENDER_MAX_CAP, lender_cap),
    )
    return min(candidates, key=lambda pair: pair[1])


def build_result(
    policy: LenderPolicy,
    *,
    decision: Decision,
    max_sanction: Decimal,
    binding: Constraint | None,
    rate_pct: Decimal | None,
    tenure_years: int,
    bounds: Bounds,
    reasons: list[ReasonTrace],
    warnings: tuple[str, ...] = (),
    monthly_saving: Decimal | None = None,
    net_benefit_note: str | None = None,
) -> EligibilityResult:
    """Assemble an EligibilityResult, computing the indicative EMI for eligible offers."""
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
        warnings=warnings,
        monthly_saving=monthly_saving,
        net_benefit_note=net_benefit_note,
    )

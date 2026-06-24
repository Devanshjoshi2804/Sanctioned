"""Income assessment and the minimum-income gate (spec §5.1, §5.5).

Assessed income is the figure all three sanction bounds are computed from: the
applicant's net monthly income, plus a haircut-adjusted share of variable pay,
plus the income of co-owner co-applicants where the policy combines it.
"""

from __future__ import annotations

from decimal import Decimal

from sanctioned.rules._support import HUNDRED, rupees
from sanctioned.schemas.borrower import BorrowerProfile, CoApplicant
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import ReasonTrace


def combinable_co_owners(profile: BorrowerProfile, policy: LenderPolicy) -> tuple[CoApplicant, ...]:
    """Co-owner co-applicants whose income this policy will combine, capped by ``max_count``."""
    if not (policy.co_applicant.allowed and policy.co_applicant.combine_income):
        return ()
    owners = tuple(co for co in profile.co_applicants if co.is_co_owner)
    return owners[: policy.co_applicant.max_count]


def assessed_income(profile: BorrowerProfile, policy: LenderPolicy) -> Decimal:
    """Total assessed monthly income used to size the loan."""
    applicant = profile.applicant
    haircut = policy.variable_pay_haircut_pct / HUNDRED
    total = applicant.net_monthly_income + applicant.variable_monthly_income * haircut
    for co in combinable_co_owners(profile, policy):
        total += co.net_monthly_income
    return total


def youngest_owner_age(profile: BorrowerProfile) -> int:
    """The youngest age among the applicant and any co-owner co-applicants.

    Most lenders compute the tenure runway off the youngest owner, which is the
    more generous (and common) treatment.
    """
    ages = [profile.applicant.age]
    ages.extend(co.age for co in profile.co_applicants if co.is_co_owner)
    return min(ages)


def check_min_income(profile: BorrowerProfile, policy: LenderPolicy) -> ReasonTrace:
    """Assert the applicant clears the policy's minimum net-monthly-income floor."""
    applicant = profile.applicant
    rule = (
        policy.min_income.self_employed
        if applicant.employment_type.is_self_employed
        else policy.min_income.salaried
    )
    is_metro = profile.property.city_tier.is_metro
    floor = rule.metro if is_metro else rule.non_metro
    income = applicant.net_monthly_income
    location = "metro" if is_metro else "non-metro"
    passed = income >= floor
    detail = (
        f"Net income {rupees(income)} clears the {location} floor"
        if passed
        else f"Net income {rupees(income)} is below the {location} floor"
    )
    return ReasonTrace(
        code="MIN_INCOME",
        rule="Minimum net monthly income",
        passed=passed,
        value=rupees(income),
        threshold=f"{rupees(floor)} ({location})",
        detail=detail,
    )

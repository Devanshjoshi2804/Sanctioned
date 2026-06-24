"""Effective tenure and the maximum-age gate (spec §5.3).

The effective tenure is the most constraining of: the policy's maximum tenure
(or a property-type override), the age runway to maturity for the youngest owner,
and the tenure the borrower actually requested. A non-positive runway means the
youngest owner is already past the maturity age — a hard rejection.
"""

from __future__ import annotations

from dataclasses import dataclass

from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.policy import AgeBlock, LenderPolicy
from sanctioned.schemas.result import ReasonTrace


@dataclass(frozen=True)
class TenureOutcome:
    """Result of the age/tenure rule."""

    effective_years: int
    rejected: bool  # True when the age runway is exhausted (AGE_MAX)
    trace: ReasonTrace


def _age_block(profile: BorrowerProfile, policy: LenderPolicy) -> AgeBlock:
    if profile.applicant.employment_type.is_self_employed:
        return policy.age.self_employed
    return policy.age.salaried


def effective_tenure(
    profile: BorrowerProfile,
    policy: LenderPolicy,
    *,
    youngest_age: int,
    property_tenure_override: int | None,
) -> TenureOutcome:
    """Compute the effective tenure in years and the age-runway verdict."""
    block = _age_block(profile, policy)
    runway = block.max_at_maturity - youngest_age
    policy_max = property_tenure_override or policy.tenure.max_years
    requested = profile.loan_request.requested_tenure_years

    effective = min(policy_max, runway, requested)
    rejected = effective <= 0

    detail = (
        f"Youngest owner aged {youngest_age}; tenure capped at {effective}y "
        f"(policy {policy_max}y, runway {runway}y, requested {requested}y)"
        if not rejected
        else f"Youngest owner aged {youngest_age} leaves no tenure runway "
        f"to maturity age {block.max_at_maturity}"
    )
    trace = ReasonTrace(
        code="AGE_MAX",
        rule="Age & tenure runway",
        passed=not rejected,
        value=f"age {youngest_age}, runway {runway}y",
        threshold=f"matures by {block.max_at_maturity}, max {policy_max}y",
        detail=detail,
    )
    return TenureOutcome(effective_years=effective, rejected=rejected, trace=trace)

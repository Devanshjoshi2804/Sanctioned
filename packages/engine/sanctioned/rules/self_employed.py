"""Self-employed eligibility gates: business vintage and ITR history (spec §5.1).

These gates apply only to self-employed applicants. Failing either is a hard
rejection (``SE_VINTAGE`` / ``SE_ITR``). Salaried applicants skip the rule and
produce no traces.
"""

from __future__ import annotations

from dataclasses import dataclass

from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import ReasonTrace


@dataclass(frozen=True)
class SelfEmployedOutcome:
    """Result of the self-employed gates."""

    rejected: bool
    traces: tuple[ReasonTrace, ...]


def evaluate_self_employed(profile: BorrowerProfile, policy: LenderPolicy) -> SelfEmployedOutcome:
    """Check business vintage and ITR-year requirements for the self-employed."""
    applicant = profile.applicant
    if not applicant.employment_type.is_self_employed:
        return SelfEmployedOutcome(rejected=False, traces=())

    rule = policy.self_employed

    vintage_ok = applicant.business_vintage_years >= rule.min_business_vintage_years
    vintage_trace = ReasonTrace(
        code="SE_VINTAGE",
        rule="Self-employed business vintage",
        passed=vintage_ok,
        value=f"{applicant.business_vintage_years}y",
        threshold=f">= {rule.min_business_vintage_years}y",
        detail=(
            f"Business vintage {applicant.business_vintage_years}y "
            f"{'meets' if vintage_ok else 'is below'} the "
            f"{rule.min_business_vintage_years}y minimum"
        ),
    )

    itr_ok = applicant.itr_years_available >= rule.itr_years_required
    itr_trace = ReasonTrace(
        code="SE_ITR",
        rule="Self-employed ITR history",
        passed=itr_ok,
        value=f"{applicant.itr_years_available}y",
        threshold=f">= {rule.itr_years_required}y",
        detail=(
            f"{applicant.itr_years_available} ITR year(s) available; "
            f"{rule.itr_years_required} required"
        ),
    )

    return SelfEmployedOutcome(
        rejected=not (vintage_ok and itr_ok),
        traces=(vintage_trace, itr_trace),
    )

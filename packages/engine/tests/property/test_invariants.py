"""Property-based invariants for the matching engine (spec §8.2).

Each invariant is its own test. Together they assert the engine's economic
guarantees hold across the whole input space, not just the golden personas:
monotonicity in income/credit/obligations, the hard ceilings (LTV, FOIR,
tenure, min-loan), determinism, and reason-trace completeness.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from sanctioned.engine import match
from sanctioned.registry import load_registry
from sanctioned.rules.employer import resolve_employer_perks
from sanctioned.rules.foir import FOIR_TOTAL_CEILING_PCT, select_cap_pct
from sanctioned.rules.income import assessed_income, youngest_owner_age
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.enums import Decision
from sanctioned.schemas.policy import FoirBand, LenderPolicy
from sanctioned.schemas.result import EligibilityResult, MatchResult
from tests.property.strategies import (
    add_co_owner,
    borrowers,
    with_cibil,
    with_income,
    with_obligations,
)

_REGISTRY = load_registry(Path(__file__).resolve().parents[2] / "policies")
_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_EPS = Decimal("1")  # whole-rupee rounding tolerance
_HUNDRED = Decimal(100)

# Modest example counts keep the suite fast in CI; deadline disabled to avoid
# timing flakiness on shared runners.
_settings = settings(max_examples=60, deadline=None)


def _by_lender(result: MatchResult) -> dict[str, EligibilityResult]:
    return {item.lender_id: item for item in result.results}


def _foir_bands(profile: BorrowerProfile, policy: LenderPolicy) -> tuple[FoirBand, ...]:
    if profile.applicant.employment_type.is_self_employed:
        return policy.foir.self_employed
    return policy.foir.salaried


@_settings
@given(profile=borrowers(), bump=st.integers(min_value=1, max_value=80000))
def test_income_monotonic(profile: BorrowerProfile, bump: int) -> None:
    """Raising income never lowers any lender's max sanction."""
    base = _by_lender(match(profile, _REGISTRY))
    richer = with_income(profile, profile.applicant.net_monthly_income + Decimal(bump))
    raised = _by_lender(match(richer, _REGISTRY))
    for lender_id, low in base.items():
        assert raised[lender_id].max_sanction >= low.max_sanction


@_settings
@given(profile=borrowers())
def test_ltv_ceiling(profile: BorrowerProfile) -> None:
    """No sanction exceeds the property value times the most generous LTV band."""
    for result in match(profile, _REGISTRY).results:
        policy = _REGISTRY.get(result.lender_id)
        max_band_ltv = max(band.max_ltv_pct for band in policy.ltv_bands)
        ceiling = profile.property.value * max_band_ltv / _HUNDRED
        assert result.max_sanction <= ceiling + _EPS


@_settings
@given(profile=borrowers())
def test_foir_ceiling(profile: BorrowerProfile) -> None:
    """An eligible offer's EMI never exceeds the FOIR headroom it was sized against."""
    for result in match(profile, _REGISTRY).results:
        if result.indicative_emi is None:
            continue
        policy = _REGISTRY.get(result.lender_id)
        assessed = assessed_income(profile, policy)
        base_cap = select_cap_pct(_foir_bands(profile, policy), assessed)
        perks = resolve_employer_perks(profile, policy)
        effective_cap = min(base_cap + perks.foir_bonus_pct, FOIR_TOTAL_CEILING_PCT)
        headroom = assessed * effective_cap / _HUNDRED - profile.existing_monthly_obligations
        assert result.indicative_emi <= headroom + _EPS


@_settings
@given(profile=borrowers(), co_income=st.integers(min_value=1, max_value=150000))
def test_co_owner_non_negative(profile: BorrowerProfile, co_income: int) -> None:
    """Adding an earning co-owner of the same age never lowers a sanction."""
    base = _by_lender(match(profile, _REGISTRY))
    # Same age as the applicant => the tenure runway is unchanged.
    augmented = add_co_owner(profile, income=Decimal(co_income), age=profile.applicant.age)
    with_co = _by_lender(match(augmented, _REGISTRY))
    for lender_id, before in base.items():
        assert with_co[lender_id].max_sanction >= before.max_sanction


@_settings
@given(
    profile=borrowers(),
    a=st.integers(min_value=300, max_value=900),
    b=st.integers(min_value=300, max_value=900),
)
def test_cibil_monotonic(profile: BorrowerProfile, a: int, b: int) -> None:
    """Lowering CIBIL never adds an APPROVE lender."""
    low_score, high_score = sorted((a, b))
    low = match(with_cibil(profile, low_score), _REGISTRY)
    high = match(with_cibil(profile, high_score), _REGISTRY)
    approve_low = sum(r.decision is Decision.APPROVE for r in low.results)
    approve_high = sum(r.decision is Decision.APPROVE for r in high.results)
    assert approve_low <= approve_high


@_settings
@given(profile=borrowers(), extra=st.integers(min_value=1, max_value=100000))
def test_obligation_monotonic(profile: BorrowerProfile, extra: int) -> None:
    """Raising existing obligations never raises a sanction."""
    base = _by_lender(match(profile, _REGISTRY))
    heavier = with_obligations(profile, profile.existing_monthly_obligations + Decimal(extra))
    burdened = _by_lender(match(heavier, _REGISTRY))
    for lender_id, before in base.items():
        assert burdened[lender_id].max_sanction <= before.max_sanction


@_settings
@given(profile=borrowers())
def test_tenure_bound(profile: BorrowerProfile) -> None:
    """Effective tenure stays within policy and matures before the maturity age."""
    youngest = youngest_owner_age(profile)
    for result in match(profile, _REGISTRY).results:
        policy = _REGISTRY.get(result.lender_id)
        assert result.effective_tenure_years <= policy.tenure.max_years
        if result.eligible:
            block = (
                policy.age.self_employed
                if profile.applicant.employment_type.is_self_employed
                else policy.age.salaried
            )
            assert youngest + result.effective_tenure_years <= block.max_at_maturity


@_settings
@given(profile=borrowers())
def test_determinism(profile: BorrowerProfile) -> None:
    """Identical inputs produce identical, identically-ordered output."""
    first = match(profile, _REGISTRY, generated_at=_FIXED_TIME)
    second = match(profile, _REGISTRY, generated_at=_FIXED_TIME)
    assert first == second


@_settings
@given(profile=borrowers())
def test_min_loan_floor(profile: BorrowerProfile) -> None:
    """An eligible offer is never below the lender's minimum loan size."""
    for result in match(profile, _REGISTRY).results:
        if result.eligible:
            assert result.max_sanction >= _REGISTRY.get(result.lender_id).limits.min_loan


@_settings
@given(profile=borrowers())
def test_reason_completeness(profile: BorrowerProfile) -> None:
    """Every result carries traces; every rejection carries a failed trace."""
    for result in match(profile, _REGISTRY).results:
        assert len(result.reasons) >= 1
        if result.decision is Decision.REJECT:
            assert any(not trace.passed for trace in result.reasons)

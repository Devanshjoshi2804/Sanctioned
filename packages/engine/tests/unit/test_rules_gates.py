"""Unit tests for the income and gate rules (income, age/tenure, CIBIL, employer,
self-employed, property)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from sanctioned.registry import load_policy
from sanctioned.rules.age_tenure import effective_tenure
from sanctioned.rules.cibil import evaluate_cibil
from sanctioned.rules.employer import resolve_employer_perks
from sanctioned.rules.income import (
    assessed_income,
    check_min_income,
    combinable_co_owners,
    youngest_owner_age,
)
from sanctioned.rules.property_ import evaluate_property
from sanctioned.rules.self_employed import evaluate_self_employed
from sanctioned.schemas.enums import (
    CityTier,
    Decision,
    EmployerCategory,
    EmploymentType,
    PropertyType,
)
from sanctioned.schemas.policy import LenderPolicy
from tests.factories import make_co_owner, make_profile


@pytest.fixture
def psu(policies_dir: Path) -> LenderPolicy:
    return load_policy(policies_dir / "psu_bank.yaml")


class TestAssessedIncome:
    def test_applies_variable_pay_haircut(self, psu: LenderPolicy) -> None:
        # 80,000 net + 50% of 20,000 variable = 90,000 (psu haircut is 50%).
        profile = make_profile(net_monthly_income="80000", variable_monthly_income="20000")
        assert assessed_income(profile, psu) == Decimal("90000")

    def test_combines_co_owner_income(self, psu: LenderPolicy) -> None:
        profile = make_profile(
            net_monthly_income="80000", co_applicants=[make_co_owner(net_monthly_income="40000")]
        )
        assert assessed_income(profile, psu) == Decimal("120000")

    def test_ignores_non_owner_co_applicant(self, psu: LenderPolicy) -> None:
        profile = make_profile(
            co_applicants=[make_co_owner(net_monthly_income="40000", is_co_owner=False)]
        )
        assert assessed_income(profile, psu) == Decimal("80000")
        assert combinable_co_owners(profile, psu) == ()

    def test_caps_combined_co_owners_at_policy_max(self, psu: LenderPolicy) -> None:
        # psu max_count is 2; a third co-owner's income must not be combined.
        cos = [make_co_owner(net_monthly_income="10000") for _ in range(3)]
        profile = make_profile(net_monthly_income="80000", co_applicants=cos)
        assert assessed_income(profile, psu) == Decimal("100000")  # 80000 + 2*10000


class TestYoungestOwnerAge:
    def test_uses_youngest_co_owner(self, psu: LenderPolicy) -> None:
        profile = make_profile(age=50, co_applicants=[make_co_owner(age=30)])
        assert youngest_owner_age(profile) == 30

    def test_ignores_non_owner_for_runway(self, psu: LenderPolicy) -> None:
        profile = make_profile(age=50, co_applicants=[make_co_owner(age=25, is_co_owner=False)])
        assert youngest_owner_age(profile) == 50


class TestMinIncome:
    def test_metro_floor_applies_to_metro_and_tier1(self, psu: LenderPolicy) -> None:
        # psu salaried metro floor is 25,000.
        ok = check_min_income(
            make_profile(net_monthly_income="25000", city_tier=CityTier.TIER_1), psu
        )
        assert ok.passed is True
        below = check_min_income(
            make_profile(net_monthly_income="24999", city_tier=CityTier.METRO), psu
        )
        assert below.passed is False

    def test_non_metro_floor_is_lower(self, psu: LenderPolicy) -> None:
        # 20,000 fails metro (25k) but clears non-metro (18k).
        result = check_min_income(
            make_profile(net_monthly_income="20000", city_tier=CityTier.TIER_2), psu
        )
        assert result.passed is True


class TestEffectiveTenure:
    def test_capped_by_age_runway(self, psu: LenderPolicy) -> None:
        # Salaried maturity 60; age 50 -> 10y runway, below requested 20y and policy 30y.
        outcome = effective_tenure(
            make_profile(age=50), psu, youngest_age=50, property_tenure_override=None
        )
        assert outcome.effective_years == 10
        assert outcome.rejected is False

    def test_capped_by_requested_tenure(self, psu: LenderPolicy) -> None:
        outcome = effective_tenure(
            make_profile(age=30, requested_tenure_years=15),
            psu,
            youngest_age=30,
            property_tenure_override=None,
        )
        assert outcome.effective_years == 15

    def test_no_runway_is_rejected(self, psu: LenderPolicy) -> None:
        outcome = effective_tenure(
            make_profile(age=60), psu, youngest_age=60, property_tenure_override=None
        )
        assert outcome.rejected is True
        assert outcome.trace.passed is False


class TestCibil:
    def test_prime_score_approves_with_rate(self, psu: LenderPolicy) -> None:
        outcome = evaluate_cibil(make_profile(cibil=820), psu)
        assert outcome.decision is Decision.APPROVE
        assert outcome.base_rate_pct == Decimal("8.10")
        assert outcome.rejected is False

    def test_below_floor_is_rejected(self, psu: LenderPolicy) -> None:
        outcome = evaluate_cibil(make_profile(cibil=680), psu)
        assert outcome.rejected is True
        assert outcome.base_rate_pct is None

    def test_thin_file_refers(self, psu: LenderPolicy) -> None:
        outcome = evaluate_cibil(make_profile(cibil=-1), psu)
        assert outcome.refer is True
        assert outcome.base_rate_pct == Decimal("9.75")


class TestEmployerPerks:
    def test_super_cat_earns_bonus(self, psu: LenderPolicy) -> None:
        perks = resolve_employer_perks(
            make_profile(employer_category=EmployerCategory.SUPER_CAT), psu
        )
        assert perks.foir_bonus_pct == Decimal("5")
        assert perks.rate_discount_bps == 10
        assert perks.trace is not None

    def test_uncategorized_earns_nothing(self, psu: LenderPolicy) -> None:
        perks = resolve_employer_perks(make_profile(), psu)
        assert perks.foir_bonus_pct == Decimal("0")
        assert perks.trace is None


class TestSelfEmployed:
    def test_salaried_skips_gates(self, psu: LenderPolicy) -> None:
        outcome = evaluate_self_employed(make_profile(), psu)
        assert outcome.rejected is False
        assert outcome.traces == ()

    def test_insufficient_vintage_rejects(self, psu: LenderPolicy) -> None:
        profile = make_profile(
            employment_type=EmploymentType.SELF_EMPLOYED_BUSINESS,
            business_vintage_years="1",
            itr_years_available=3,
        )
        outcome = evaluate_self_employed(profile, psu)
        assert outcome.rejected is True

    def test_sufficient_history_passes(self, psu: LenderPolicy) -> None:
        profile = make_profile(
            employment_type=EmploymentType.SELF_EMPLOYED_PROFESSIONAL,
            business_vintage_years="5",
            itr_years_available=3,
        )
        outcome = evaluate_self_employed(profile, psu)
        assert outcome.rejected is False


class TestProperty:
    def test_unlisted_type_defaults_allowed(self, psu: LenderPolicy) -> None:
        outcome = evaluate_property(make_profile(property_type=PropertyType.APPROVED_RESALE), psu)
        assert outcome.allowed is True
        assert outcome.ltv_override_pct is None

    def test_under_construction_carries_ltv_override(self, psu: LenderPolicy) -> None:
        outcome = evaluate_property(
            make_profile(property_type=PropertyType.UNDER_CONSTRUCTION), psu
        )
        assert outcome.allowed is True
        assert outcome.ltv_override_pct == Decimal("80")

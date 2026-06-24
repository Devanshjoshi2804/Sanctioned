"""Unit tests for the three sanction bounds: FOIR, LTV, and NMI multiplier.

Expected values are derived independently of the bound implementations — from the
PSU policy's published numbers and the already-verified ``emi`` math — so these
tests pin behaviour rather than mirror code.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from sanctioned.emi import max_principal
from sanctioned.registry import load_policy
from sanctioned.rules.foir import foir_bound
from sanctioned.rules.ltv import ltv_bound
from sanctioned.rules.multiplier import multiplier_bound
from sanctioned.schemas.policy import LenderPolicy


@pytest.fixture
def psu(policies_dir: Path) -> LenderPolicy:
    return load_policy(policies_dir / "psu_bank.yaml")


class TestMultiplierBound:
    def test_is_max_multiplier_times_income(self, psu: LenderPolicy) -> None:
        # PSU nmi_multiplier.max is 60; 60 * 80,000 = 4,800,000.
        bound, trace = multiplier_bound(Decimal("80000"), psu)
        assert bound == Decimal("4800000")
        assert trace.code == "MULTIPLIER_CAP"


class TestLtvBound:
    def test_selects_self_consistent_band(self, psu: LenderPolicy) -> None:
        # A ₹50L property: 90% would imply ₹45L (above the ₹30L band ceiling), so
        # the 80% band applies -> ₹40,00,000.
        outcome = ltv_bound(property_value=Decimal("5000000"), policy=psu)
        assert outcome.effective_ltv_pct == Decimal("80")
        assert outcome.bound == Decimal("4000000")

    def test_small_loan_uses_top_ltv_band(self, psu: LenderPolicy) -> None:
        # A ₹20L property at 90% implies ₹18L, within the ₹30L band -> 90% applies.
        outcome = ltv_bound(property_value=Decimal("2000000"), policy=psu)
        assert outcome.effective_ltv_pct == Decimal("90")
        assert outcome.bound == Decimal("1800000")

    def test_property_override_caps_ltv(self, psu: LenderPolicy) -> None:
        outcome = ltv_bound(
            property_value=Decimal("5000000"), policy=psu, ltv_override_pct=Decimal("70")
        )
        assert outcome.effective_ltv_pct == Decimal("70")
        assert outcome.bound == Decimal("3500000")

    def test_product_override_caps_ltv(self, psu: LenderPolicy) -> None:
        outcome = ltv_bound(
            property_value=Decimal("2000000"), policy=psu, product_max_ltv_pct=Decimal("75")
        )
        assert outcome.effective_ltv_pct == Decimal("75")


class TestFoirBound:
    def test_uses_income_band_cap_and_emi_math(self, psu: LenderPolicy) -> None:
        # 80,000 income -> 55% band; available EMI = 44,000; principal via PV math.
        expected_emi = Decimal("80000") * Decimal("55") / Decimal("100")
        expected_bound = max_principal(expected_emi, Decimal("8.10"), 240)
        outcome = foir_bound(
            assessed_income=Decimal("80000"),
            existing_obligations=Decimal("0"),
            policy=psu,
            is_self_employed=False,
            foir_bonus_pct=Decimal("0"),
            rate_pct=Decimal("8.10"),
            tenure_months=240,
        )
        assert outcome.effective_cap_pct == Decimal("55")
        assert outcome.available_emi == expected_emi
        assert outcome.bound == expected_bound
        assert outcome.rejected is False

    def test_existing_obligations_reduce_headroom(self, psu: LenderPolicy) -> None:
        outcome = foir_bound(
            assessed_income=Decimal("80000"),
            existing_obligations=Decimal("10000"),
            policy=psu,
            is_self_employed=False,
            foir_bonus_pct=Decimal("0"),
            rate_pct=Decimal("8.10"),
            tenure_months=240,
        )
        # 55% of 80,000 = 44,000, minus 10,000 obligations = 34,000 headroom.
        assert outcome.available_emi == Decimal("34000")

    def test_no_headroom_is_rejected(self, psu: LenderPolicy) -> None:
        outcome = foir_bound(
            assessed_income=Decimal("40000"),
            existing_obligations=Decimal("30000"),  # exceeds 55% * 40,000 = 22,000
            policy=psu,
            is_self_employed=False,
            foir_bonus_pct=Decimal("0"),
            rate_pct=Decimal("8.10"),
            tenure_months=240,
        )
        assert outcome.rejected is True
        assert outcome.bound == Decimal("0")
        assert any(t.code == "FOIR_NO_HEADROOM" for t in outcome.traces)

    def test_employer_bonus_is_capped_at_ceiling(self, psu: LenderPolicy) -> None:
        # High income -> 60% band; +10% bonus would give 70%, clamped to the 65% ceiling.
        outcome = foir_bound(
            assessed_income=Decimal("150000"),
            existing_obligations=Decimal("0"),
            policy=psu,
            is_self_employed=False,
            foir_bonus_pct=Decimal("10"),
            rate_pct=Decimal("8.10"),
            tenure_months=240,
        )
        assert outcome.effective_cap_pct == Decimal("65")

"""Integration tests for the balance-transfer and top-up products."""

from __future__ import annotations

from decimal import Decimal

from sanctioned.engine import match
from sanctioned.registry import Registry
from sanctioned.schemas.enums import Decision, ProductType
from sanctioned.schemas.result import EligibilityResult, MatchResult
from tests.factories import make_profile


def _psu(result: MatchResult) -> EligibilityResult:
    return next(r for r in result.results if r.lender_id == "psu_bank")


class TestBalanceTransfer:
    def test_transfer_to_cheaper_lender_shows_saving(self, registry: Registry) -> None:
        profile = make_profile(
            net_monthly_income="90000",
            property_value="7000000",
            product_type=ProductType.BALANCE_TRANSFER,
            existing_loan_outstanding="4000000",
            existing_rate_pct="9.5",
        )
        psu = _psu(match(profile, registry))
        assert psu.decision is Decision.APPROVE
        assert psu.max_sanction == Decimal("4000000")  # full outstanding fits capacity
        assert psu.monthly_saving is not None and psu.monthly_saving > 0
        assert psu.net_benefit_note is not None

    def test_capacity_below_outstanding_refers(self, registry: Registry) -> None:
        # Modest income but a large outstanding the lender cannot fully fund.
        profile = make_profile(
            net_monthly_income="40000",
            property_value="6000000",
            product_type=ProductType.BALANCE_TRANSFER,
            existing_loan_outstanding="5000000",
            existing_rate_pct="9.5",
        )
        psu = _psu(match(profile, registry))
        assert psu.decision is Decision.REFER
        assert any("only part" in w for w in psu.warnings)


class TestTopUp:
    def test_top_up_within_combined_ltv_approves(self, registry: Registry) -> None:
        profile = make_profile(
            net_monthly_income="120000",
            property_value="9000000",
            product_type=ProductType.TOP_UP,
            existing_loan_outstanding="3000000",
            requested_amount="1000000",
        )
        psu = _psu(match(profile, registry))
        assert psu.decision is Decision.APPROVE
        assert psu.max_sanction == Decimal("1000000")
        assert any(t.code == "TOPUP_LTV" and t.passed for t in psu.reasons)

    def test_combined_exposure_over_ltv_is_rejected(self, registry: Registry) -> None:
        # Outstanding alone already exceeds the 75% combined-LTV cap on the property.
        profile = make_profile(
            net_monthly_income="200000",
            property_value="6000000",  # 75% cap = 4,500,000
            product_type=ProductType.TOP_UP,
            existing_loan_outstanding="5000000",  # already above the cap
            requested_amount="1000000",
        )
        psu = _psu(match(profile, registry))
        assert psu.decision is Decision.REJECT
        assert any(t.code == "TOPUP_LTV" and not t.passed for t in psu.reasons)

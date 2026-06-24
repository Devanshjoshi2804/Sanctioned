"""Unit tests for the EMI / present-value money math.

These pin the formulas in §5.2 of the spec against hand-computed, textbook values
and check the algebraic relationship between ``emi`` and ``max_principal`` (each is
the inverse of the other). All arithmetic is in :class:`~decimal.Decimal`.
"""

from decimal import Decimal

import pytest

from sanctioned.emi import emi, max_principal, monthly_rate, round_rupees


class TestMonthlyRate:
    def test_converts_annual_percent_to_monthly_fraction(self) -> None:
        # 12% per annum -> 1% per month -> 0.01 as a fraction.
        assert monthly_rate(Decimal("12")) == Decimal("0.01")

    def test_zero_rate_is_zero(self) -> None:
        assert monthly_rate(Decimal("0")) == Decimal("0")


class TestEmi:
    def test_matches_textbook_value(self) -> None:
        # ₹10,00,000 at 10% p.a. over 120 months is the well-known ₹13,215 EMI.
        result = emi(Decimal("1000000"), Decimal("10"), 120)
        assert round_rupees(result) == Decimal("13215")

    def test_zero_rate_is_principal_over_months(self) -> None:
        # With no interest, the EMI is simply principal spread evenly.
        result = emi(Decimal("120000"), Decimal("0"), 12)
        assert result == Decimal("10000")

    def test_single_month_tenure_repays_principal_plus_one_month_interest(self) -> None:
        # n = 1: EMI = P * (1 + r).
        result = emi(Decimal("100000"), Decimal("12"), 1)
        assert round_rupees(result) == Decimal("101000")

    def test_rejects_non_positive_tenure(self) -> None:
        with pytest.raises(ValueError, match="tenure"):
            emi(Decimal("100000"), Decimal("10"), 0)


class TestMaxPrincipal:
    def test_matches_spec_worked_example(self) -> None:
        # §8.3: a ₹40,000 EMI at 8.5% p.a. over 20 years supports ~₹46-48 lakh.
        result = max_principal(Decimal("40000"), Decimal("8.5"), 240)
        assert Decimal("4600000") <= result <= Decimal("4800000")

    def test_zero_rate_is_emi_times_months(self) -> None:
        result = max_principal(Decimal("10000"), Decimal("0"), 12)
        assert result == Decimal("120000")

    def test_rejects_non_positive_tenure(self) -> None:
        with pytest.raises(ValueError, match="tenure"):
            max_principal(Decimal("40000"), Decimal("10"), 0)


class TestInverseRelationship:
    @pytest.mark.parametrize(
        ("principal", "rate", "months"),
        [
            (Decimal("1000000"), Decimal("10"), 120),
            (Decimal("4609200"), Decimal("8.5"), 240),
            (Decimal("2500000"), Decimal("0"), 180),
            (Decimal("750000"), Decimal("7.25"), 60),
        ],
    )
    def test_max_principal_inverts_emi(
        self, principal: Decimal, rate: Decimal, months: int
    ) -> None:
        # Feeding an EMI back through max_principal must recover the principal.
        installment = emi(principal, rate, months)
        recovered = max_principal(installment, rate, months)
        assert round_rupees(recovered) == round_rupees(principal)


class TestRoundRupees:
    def test_rounds_half_up_to_whole_rupee(self) -> None:
        assert round_rupees(Decimal("100.50")) == Decimal("101")

    def test_truncates_fraction_below_half(self) -> None:
        assert round_rupees(Decimal("100.49")) == Decimal("100")

    def test_already_whole_is_unchanged(self) -> None:
        assert round_rupees(Decimal("100")) == Decimal("100")

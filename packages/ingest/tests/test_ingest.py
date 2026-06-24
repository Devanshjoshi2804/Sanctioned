"""Tests for sandbox AA ingestion: statement -> derived financials -> autofill."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sanctioned_ingest.autofill import profile_autofill
from sanctioned_ingest.derive import derive_financials
from sanctioned_ingest.source import MockStatementSource, SetuAaSource


class TestMockStatement:
    def test_has_salary_and_emi_each_month(self) -> None:
        statement = MockStatementSource(months=4).fetch()
        assert len(statement.months()) == 4
        salary = [t for t in statement.transactions if t.category.value == "SALARY"]
        emi = [t for t in statement.transactions if t.category.value == "EMI"]
        assert len(salary) == 4
        assert len(emi) == 4

    def test_is_deterministic(self) -> None:
        assert MockStatementSource().fetch() == MockStatementSource().fetch()


class TestDerive:
    def test_derives_income_and_obligations(self) -> None:
        statement = MockStatementSource(
            monthly_salary=Decimal("90000"), monthly_emi=Decimal("12000"), months=4
        ).fetch()
        derived = derive_financials(statement)
        assert derived.net_monthly_income == Decimal("90000")
        assert derived.existing_monthly_obligations == Decimal("12000")
        assert derived.salary_regularity == "REGULAR"
        assert derived.regularity_score == Decimal("1.00")
        assert derived.months_observed == 4
        assert "sandbox" in derived.disclaimer.lower()

    def test_missing_salary_month_lowers_regularity(self) -> None:
        statement = MockStatementSource(months=4, skip_salary_month=2).fetch()
        derived = derive_financials(statement)
        assert derived.regularity_score == Decimal("0.75")
        assert derived.salary_regularity == "IRREGULAR"
        # Income still derives from the months that do have salary.
        assert derived.net_monthly_income == Decimal("90000")

    def test_single_month_is_insufficient(self) -> None:
        statement = MockStatementSource(months=1).fetch()
        derived = derive_financials(statement)
        assert derived.salary_regularity == "INSUFFICIENT"


class TestAutofill:
    def test_maps_to_form_fields(self) -> None:
        derived = derive_financials(MockStatementSource().fetch())
        fields = profile_autofill(derived)
        assert fields["net_monthly_income"] == "90000"
        assert fields["existing_monthly_obligations"] == "12000"


class TestSetuSeam:
    def test_setu_source_is_inert_without_wiring(self) -> None:
        with pytest.raises(NotImplementedError, match="Setu AA sandbox"):
            SetuAaSource().fetch()

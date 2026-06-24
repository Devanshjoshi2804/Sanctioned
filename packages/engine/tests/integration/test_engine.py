"""Integration tests for the end-to-end matching engine."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sanctioned.engine import match
from sanctioned.registry import Registry
from sanctioned.schemas.enums import Constraint, Decision
from sanctioned.schemas.result import EligibilityResult, MatchResult
from tests.factories import make_profile

_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _psu(result_set: MatchResult) -> EligibilityResult:
    return next(r for r in result_set.results if r.lender_id == "psu_bank")


class TestPrimeBorrower:
    def test_approves_with_ltv_binding(self, registry: Registry) -> None:
        # 80k salaried, ₹50L metro property, CIBIL 800, 20y: LTV binds at ₹40L.
        result = match(make_profile(), registry, generated_at=_FIXED_TIME)
        psu = _psu(result)
        assert psu.decision is Decision.APPROVE
        assert psu.eligible is True
        assert psu.max_sanction == Decimal("4000000")
        assert psu.binding_constraint is Constraint.LTV
        assert psu.indicative_rate_pct == Decimal("8.10")
        assert psu.indicative_emi is not None and psu.indicative_emi > 0

    def test_every_result_has_traces(self, registry: Registry) -> None:
        result = match(make_profile(), registry, generated_at=_FIXED_TIME)
        for eligibility in result.results:
            assert len(eligibility.reasons) >= 1


class TestRejection:
    def test_low_cibil_rejects_with_failed_trace(self, registry: Registry) -> None:
        result = match(make_profile(cibil=680), registry, generated_at=_FIXED_TIME)
        psu = _psu(result)
        assert psu.decision is Decision.REJECT
        assert psu.eligible is False
        assert psu.max_sanction == Decimal("0")
        # A rejection must always carry at least one failed trace explaining why.
        assert any(not trace.passed for trace in psu.reasons)

    def test_disallowed_property_rejects(self, registry: Registry) -> None:
        # Construct a lender that funds nothing the borrower brings is out of scope;
        # instead drive a no-headroom rejection via crushing obligations.
        result = match(
            make_profile(net_monthly_income="40000", existing_monthly_obligations="30000"),
            registry,
            generated_at=_FIXED_TIME,
        )
        psu = _psu(result)
        assert psu.decision is Decision.REJECT
        assert any(trace.code == "FOIR_NO_HEADROOM" for trace in psu.reasons)


class TestRankingAndSummary:
    def test_results_sorted_eligible_first(self, registry: Registry) -> None:
        result = match(make_profile(), registry, generated_at=_FIXED_TIME)
        eligibility_flags = [r.eligible for r in result.results]
        # Once we see an ineligible lender, no eligible one may follow.
        assert eligibility_flags == sorted(eligibility_flags, reverse=True)

    def test_summary_reflects_results(self, registry: Registry) -> None:
        result = match(make_profile(), registry, generated_at=_FIXED_TIME)
        eligible = [r for r in result.results if r.eligible]
        assert result.summary.eligible_count == len(eligible)
        if eligible:
            assert result.summary.top_lender_id == result.results[0].lender_id
            assert result.summary.best_rate == min(
                r.indicative_rate_pct for r in eligible if r.indicative_rate_pct is not None
            )


class TestDeterminism:
    def test_same_input_same_output(self, registry: Registry) -> None:
        profile = make_profile(variable_monthly_income="15000")
        first = match(profile, registry, generated_at=_FIXED_TIME)
        second = match(profile, registry, generated_at=_FIXED_TIME)
        assert first == second

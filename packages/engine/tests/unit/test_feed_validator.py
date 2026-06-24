"""Unit tests for the Pandera feed validators."""

from __future__ import annotations

from pathlib import Path

from sanctioned.registry import Registry
from sanctioned.samples import generate_personas
from sanctioned.validation.feed_validator import (
    offer_records,
    persona_records,
    render_report,
    validate_offer_feed,
    validate_persona_feed,
    write_report,
)


class TestPersonaFeed:
    def test_valid_personas_pass(self) -> None:
        report = validate_persona_feed(persona_records(generate_personas()))
        assert report.ok
        assert report.rows == len(generate_personas())

    def test_thin_file_cibil_is_accepted(self) -> None:
        report = validate_persona_feed(
            [
                {
                    "net_monthly_income": 50000.0,
                    "cibil": -1,
                    "property_value": 4000000.0,
                    "existing_obligations": 0.0,
                    "age": 35,
                }
            ]
        )
        assert report.ok

    def test_corrupt_rows_are_flagged(self) -> None:
        report = validate_persona_feed(
            [
                {
                    "net_monthly_income": -5000.0,  # non-positive income
                    "cibil": 1000,  # out of range
                    "property_value": 0.0,  # non-positive value
                    "existing_obligations": -100.0,  # negative obligations
                    "age": 15,  # below minimum
                }
            ]
        )
        assert not report.ok
        flagged = {failure.column for failure in report.failures}
        assert {"net_monthly_income", "cibil", "property_value"} <= flagged


class TestOfferFeed:
    def test_registry_offers_pass(self, registry: Registry) -> None:
        report = validate_offer_feed(offer_records(registry))
        assert report.ok

    def test_impossible_percentages_are_flagged(self) -> None:
        report = validate_offer_feed(
            [
                {
                    "lender_id": "bad",
                    "decision": "APPROVE",
                    "foir_cap_pct": 120.0,  # > 100
                    "max_ltv_pct": 95.0,  # > 90
                    "rate_pct": 8.5,
                }
            ]
        )
        assert not report.ok
        flagged = {failure.column for failure in report.failures}
        assert {"foir_cap_pct", "max_ltv_pct"} <= flagged

    def test_missing_rate_on_approvable_tier_is_flagged(self) -> None:
        report = validate_offer_feed(
            [
                {
                    "lender_id": "bad",
                    "decision": "APPROVE",
                    "foir_cap_pct": 55.0,
                    "max_ltv_pct": 80.0,
                    "rate_pct": None,  # required for non-REJECT tiers
                }
            ]
        )
        assert not report.ok


class TestReport:
    def test_render_marks_failures(self, tmp_path: Path) -> None:
        good = validate_persona_feed(persona_records(generate_personas(limit=5)))
        bad = validate_offer_feed(
            [
                {
                    "lender_id": "x",
                    "decision": "APPROVE",
                    "foir_cap_pct": 200.0,
                    "max_ltv_pct": 80.0,
                    "rate_pct": 8.0,
                }
            ]
        )
        markdown = render_report([good, bad])
        assert "PASS" in markdown and "FAIL" in markdown

        out = write_report([good, bad], tmp_path / "validation_report.md")
        assert out.exists()
        assert out.read_text(encoding="utf-8").startswith("# Feed validation report")

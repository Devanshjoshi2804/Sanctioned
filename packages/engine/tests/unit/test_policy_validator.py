"""Unit tests for the cross-field policy business-rule validator (§6).

Each test takes the valid PSU policy, breaks exactly one invariant, and asserts
the validator rejects it loudly — naming the offending field. The happy-path test
asserts the untouched policy passes.
"""

from __future__ import annotations

from typing import Any

import pytest

from sanctioned.schemas.policy import LenderPolicy
from sanctioned.validation.policy_validator import PolicyValidationError, validate_policy


def _policy(data: dict[str, Any]) -> LenderPolicy:
    return LenderPolicy.model_validate(data)


def test_valid_policy_passes(psu_policy_data: dict[str, Any]) -> None:
    validate_policy(_policy(psu_policy_data))  # must not raise


def test_error_names_the_lender(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["limits"]["min_loan"] = psu_policy_data["limits"]["max_loan"]
    with pytest.raises(PolicyValidationError) as exc:
        validate_policy(_policy(psu_policy_data))
    assert exc.value.lender_id == "psu_bank"


def test_foir_cap_above_ceiling_rejected(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["foir"]["salaried"][-1]["cap_pct"] = 75  # > 70
    with pytest.raises(PolicyValidationError, match="foir"):
        validate_policy(_policy(psu_policy_data))


def test_non_monotonic_ltv_bands_rejected(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["ltv_bands"] = [
        {"up_to_amount": 3000000, "max_ltv_pct": 80},
        {"up_to_amount": 7500000, "max_ltv_pct": 90},  # rises as amount grows
        {"up_to_amount": None, "max_ltv_pct": 75},
    ]
    with pytest.raises(PolicyValidationError, match="ltv"):
        validate_policy(_policy(psu_policy_data))


def test_cibil_coverage_gap_rejected(psu_policy_data: dict[str, Any]) -> None:
    # Drop the 300..699 band so the 300..699 range is no longer covered.
    psu_policy_data["cibil_tiers"] = [
        tier for tier in psu_policy_data["cibil_tiers"] if tier["min_score"] != 300
    ]
    with pytest.raises(PolicyValidationError, match="cibil"):
        validate_policy(_policy(psu_policy_data))


def test_cibil_overlap_rejected(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["cibil_tiers"][1]["max_score"] = 810  # overlaps the 800..900 band
    with pytest.raises(PolicyValidationError, match="cibil"):
        validate_policy(_policy(psu_policy_data))


def test_age_maturity_not_above_entry_rejected(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["age"]["salaried"]["max_at_maturity"] = 20  # < min_entry 21
    with pytest.raises(PolicyValidationError, match="age"):
        validate_policy(_policy(psu_policy_data))


def test_min_loan_not_below_max_loan_rejected(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["limits"]["min_loan"] = 200000000  # > max_loan
    with pytest.raises(PolicyValidationError, match="limits"):
        validate_policy(_policy(psu_policy_data))


def test_missing_rate_for_non_reject_tier_rejected(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["cibil_tiers"][0]["rate_pct"] = None  # APPROVE tier with no rate
    with pytest.raises(PolicyValidationError, match="cibil"):
        validate_policy(_policy(psu_policy_data))


def test_blank_disclaimer_rejected(psu_policy_data: dict[str, Any]) -> None:
    psu_policy_data["disclaimer"] = "   "  # whitespace-only is not a disclaimer
    with pytest.raises(PolicyValidationError, match="disclaimer"):
        validate_policy(_policy(psu_policy_data))

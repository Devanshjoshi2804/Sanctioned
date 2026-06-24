"""Unit tests for policy loading and the in-memory registry."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from sanctioned.registry import load_policy, load_registry
from sanctioned.schemas.enums import LenderType
from sanctioned.validation.policy_validator import PolicyValidationError


class TestLoadPolicy:
    def test_parses_psu_bank(self, policies_dir: Path) -> None:
        policy = load_policy(policies_dir / "psu_bank.yaml")
        assert policy.lender_id == "psu_bank"
        assert policy.lender_type is LenderType.PUBLIC_BANK
        assert policy.limits.max_loan == Decimal("100000000")

    def test_rates_load_as_exact_decimals(self, policies_dir: Path) -> None:
        # 8.10 in YAML must become Decimal("8.10"), not a binary-float approximation.
        policy = load_policy(policies_dir / "psu_bank.yaml")
        top_tier = policy.cibil_tiers[0]
        assert top_tier.rate_pct == Decimal("8.10")


class TestLoadRegistry:
    def test_indexes_policies_by_lender_id(self, policies_dir: Path) -> None:
        registry = load_registry(policies_dir)
        assert registry.get("psu_bank").lender_name == "PSU Bank (indicative archetype)"
        assert len(registry) >= 1
        assert "psu_bank" in {policy.lender_id for policy in registry}

    def test_unknown_lender_raises_key_error(self, policies_dir: Path) -> None:
        registry = load_registry(policies_dir)
        with pytest.raises(KeyError):
            registry.get("does_not_exist")

    def test_invalid_policy_in_directory_fails_loud(self, tmp_path: Path) -> None:
        # A registry must refuse to load if any member policy is invalid.
        (tmp_path / "broken.yaml").write_text("lender_id: broken\n")
        with pytest.raises((PolicyValidationError, ValueError)):
            load_registry(tmp_path)

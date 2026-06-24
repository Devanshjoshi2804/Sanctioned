"""Shared test fixtures for the engine test suite."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from sanctioned.registry import Registry, load_policy_data, load_registry

POLICIES_DIR = Path(__file__).resolve().parent.parent / "policies"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register --update-golden to rewrite golden snapshots instead of asserting."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Rewrite golden snapshot files from current engine output.",
    )


@pytest.fixture
def policies_dir() -> Path:
    """Absolute path to the bundled lender-policy YAML directory."""
    return POLICIES_DIR


@pytest.fixture
def registry() -> Registry:
    """The full validated lender registry loaded from bundled policies."""
    return load_registry(POLICIES_DIR)


@pytest.fixture
def psu_policy_data() -> dict[str, Any]:
    """A fresh, mutable copy of the PSU policy as a raw (Decimal-safe) dict.

    Returned per-test so a test can mutate one field to construct an invalid
    variant without affecting other tests.
    """
    return copy.deepcopy(load_policy_data(POLICIES_DIR / "psu_bank.yaml"))

"""Golden regression test: the full persona spread against the lender panel.

Every synthetic persona is run through the engine and its serialised MatchResult
is compared, field for field, against a committed snapshot. Any change in engine
behaviour — intended or not — surfaces here as a per-persona diff. Snapshots are
regenerated only with an explicit ``--update-golden`` flag, so drift can never slip
in silently.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sanctioned.engine import match
from sanctioned.registry import Registry
from sanctioned.samples import generate_personas

_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_SNAPSHOT = Path(__file__).resolve().parent / "expected_match_results.json"


def _run_all(registry: Registry) -> list[dict[str, Any]]:
    """Serialise every persona's MatchResult with a fixed timestamp."""
    return [
        match(persona, registry, generated_at=_FIXED_TIME).model_dump(mode="json")
        for persona in generate_personas()
    ]


def test_dataset_has_minimum_spread() -> None:
    # The spec requires at least 300 golden personas.
    assert len(generate_personas()) >= 300


def test_golden_match_results(registry: Registry, request: pytest.FixtureRequest) -> None:
    actual = _run_all(registry)

    if request.config.getoption("--update-golden"):
        _SNAPSHOT.write_text(
            json.dumps(actual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        pytest.skip(f"Golden snapshot rewritten with {len(actual)} results")

    assert _SNAPSHOT.exists(), "golden snapshot missing — run pytest --update-golden"
    expected = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))

    assert len(actual) == len(expected), "persona count changed"
    for index, (got, want) in enumerate(zip(actual, expected, strict=True)):
        assert got == want, f"persona {index} drifted from the golden snapshot"

"""Convert the engine's dataclass reports into JSON-able dicts.

The matching models are Pydantic and serialise themselves; the policy-diff and
feed-validation reports are plain dataclasses, so we map them here. Decimals are
rendered as strings to preserve exact rupee values over the wire.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sanctioned.policy_diff import DiffReport, LenderDiff, Mover
from sanctioned.validation.feed_validator import FeedReport


def _money(value: Decimal) -> str:
    return str(value)


def serialize_mover(mover: Mover) -> dict[str, Any]:
    return {
        "persona_index": mover.persona_index,
        "base_sanction": _money(mover.base_sanction),
        "head_sanction": _money(mover.head_sanction),
        "delta": _money(mover.delta),
    }


def serialize_lender_diff(diff: LenderDiff) -> dict[str, Any]:
    return {
        "lender_id": diff.lender_id,
        "status": diff.status,
        "personas": diff.personas,
        "decision_flips": diff.decision_flips,
        "flip_breakdown": diff.flip_breakdown,
        "sanction_changed": diff.sanction_changed,
        "avg_delta": _money(diff.avg_delta),
        "median_delta": _money(diff.median_delta),
        "binding_changes": diff.binding_changes,
        "largest_movers": [serialize_mover(m) for m in diff.largest_movers],
    }


def serialize_diff_report(report: DiffReport) -> dict[str, Any]:
    return {
        "persona_count": report.persona_count,
        "total_decision_flips": report.total_decision_flips,
        "has_changes": report.has_changes,
        "lender_diffs": [serialize_lender_diff(d) for d in report.lender_diffs],
    }


def serialize_feed_report(report: FeedReport) -> dict[str, Any]:
    return {
        "feed": report.feed,
        "rows": report.rows,
        "ok": report.ok,
        "failures": [
            {
                "column": failure.column,
                "check": failure.check,
                "row": failure.row,
                "value": None if failure.value is None else str(failure.value),
            }
            for failure in report.failures
        ],
    }

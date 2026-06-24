"""Pandera data-validation for borrower-persona and lender-offer feeds (spec §6).

Where :mod:`sanctioned.validation.policy_validator` guards a single policy's
internal consistency, this module guards *tabular feeds* of data flowing into the
system — catching the kinds of corruption that schema-per-row parsing might let
through in bulk: non-positive incomes, out-of-range CIBIL scores, impossible FOIR
or LTV percentages, and missing rates on approvable tiers. Results render to a
human-readable ``validation_report.md``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

from sanctioned.registry import Registry
from sanctioned.schemas.borrower import BorrowerProfile

# --- Schemas ------------------------------------------------------------------

_CIBIL_RANGE_MESSAGE = "cibil must be -1 (thin file) or within 300..900"

PERSONA_FEED_SCHEMA = pa.DataFrameSchema(
    {
        "net_monthly_income": pa.Column(float, pa.Check.gt(0)),
        "cibil": pa.Column(
            int,
            pa.Check(
                lambda s: (s == -1) | ((s >= 300) & (s <= 900)),
                error=_CIBIL_RANGE_MESSAGE,
            ),
        ),
        "property_value": pa.Column(float, pa.Check.gt(0)),
        "existing_obligations": pa.Column(float, pa.Check.ge(0)),
        "age": pa.Column(int, pa.Check.in_range(18, 100)),
    },
    name="persona_feed",
    strict=False,
)

OFFER_FEED_SCHEMA = pa.DataFrameSchema(
    {
        "lender_id": pa.Column(str),
        "decision": pa.Column(str, pa.Check.isin(["APPROVE", "REFER", "REJECT"])),
        "foir_cap_pct": pa.Column(float, pa.Check.in_range(0, 100, include_min=False)),
        "max_ltv_pct": pa.Column(float, [pa.Check.gt(0), pa.Check.le(90)]),
        "rate_pct": pa.Column(float, pa.Check.gt(0), nullable=True),
    },
    checks=pa.Check(
        lambda df: ~((df["decision"] != "REJECT") & df["rate_pct"].isna()),
        error="rate_pct is required for every non-REJECT tier",
    ),
    name="offer_feed",
    strict=False,
)


# --- Report types -------------------------------------------------------------


@dataclass(frozen=True)
class FailureCase:
    """A single Pandera check failure."""

    column: str | None
    check: str
    row: int | None
    value: Any


@dataclass(frozen=True)
class FeedReport:
    """The outcome of validating one feed."""

    feed: str
    rows: int
    failures: tuple[FailureCase, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


# --- Validation ---------------------------------------------------------------


def _validate(
    schema: pa.DataFrameSchema, records: Iterable[dict[str, Any]], feed: str
) -> FeedReport:
    frame = pd.DataFrame(list(records))
    if frame.empty:
        return FeedReport(feed=feed, rows=0, failures=())
    try:
        schema.validate(frame, lazy=True)
    except SchemaErrors as errors:
        cases = errors.failure_cases
        failures = tuple(
            FailureCase(
                column=_optional_str(column),
                check=str(check),
                row=_optional_int(index),
                value=value,
            )
            for column, check, index, value in zip(
                cases["column"].tolist(),
                cases["check"].tolist(),
                cases["index"].tolist(),
                cases["failure_case"].tolist(),
                strict=False,
            )
        )
        return FeedReport(feed=feed, rows=len(frame), failures=failures)
    return FeedReport(feed=feed, rows=len(frame), failures=())


def _optional_str(value: Any) -> str | None:
    return None if value is None or pd.isna(value) else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None or pd.isna(value) else int(value)


def validate_persona_feed(records: Iterable[dict[str, Any]]) -> FeedReport:
    """Validate a feed of borrower personas."""
    return _validate(PERSONA_FEED_SCHEMA, records, "persona_feed")


def validate_offer_feed(records: Iterable[dict[str, Any]]) -> FeedReport:
    """Validate a feed of lender offers (one row per lender CIBIL tier)."""
    return _validate(OFFER_FEED_SCHEMA, records, "offer_feed")


# --- Feed builders (turn domain objects into tabular records) -----------------


def persona_records(profiles: Iterable[BorrowerProfile]) -> list[dict[str, Any]]:
    """Flatten borrower profiles into persona-feed rows."""
    return [
        {
            "net_monthly_income": float(profile.applicant.net_monthly_income),
            "cibil": profile.applicant.cibil,
            "property_value": float(profile.property.value),
            "existing_obligations": float(profile.existing_monthly_obligations),
            "age": profile.applicant.age,
        }
        for profile in profiles
    ]


def offer_records(registry: Registry) -> list[dict[str, Any]]:
    """Flatten a registry into offer-feed rows (one per lender CIBIL tier)."""
    rows: list[dict[str, Any]] = []
    for policy in registry:
        top_foir = max(band.cap_pct for band in policy.foir.salaried)
        top_ltv = max(band.max_ltv_pct for band in policy.ltv_bands)
        for tier in policy.cibil_tiers:
            rows.append(
                {
                    "lender_id": policy.lender_id,
                    "decision": tier.decision.value,
                    "foir_cap_pct": float(top_foir),
                    "max_ltv_pct": float(top_ltv),
                    "rate_pct": None if tier.rate_pct is None else float(tier.rate_pct),
                }
            )
    return rows


# --- Reporting ----------------------------------------------------------------


def render_report(reports: Iterable[FeedReport]) -> str:
    """Render feed reports as Markdown."""
    lines = ["# Feed validation report", ""]
    for report in reports:
        status = "✅ PASS" if report.ok else f"❌ FAIL ({len(report.failures)} issue(s))"
        lines += [
            f"## `{report.feed}`",
            "",
            f"- Rows checked: {report.rows}",
            f"- Status: {status}",
            "",
        ]
        if report.failures:
            lines += ["| Column | Check | Row | Value |", "|---|---|---|---|"]
            for f in report.failures:
                row = f.row if f.row is not None else "-"
                lines.append(f"| {f.column or '-'} | {f.check} | {row} | {f.value} |")
            lines.append("")
    return "\n".join(lines)


def write_report(reports: Iterable[FeedReport], path: Path) -> Path:
    """Write the Markdown feed report to ``path`` and return it."""
    path.write_text(render_report(reports) + "\n", encoding="utf-8")
    return path

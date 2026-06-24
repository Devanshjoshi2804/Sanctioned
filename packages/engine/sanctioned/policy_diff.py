"""Policy-diff impact report (spec §7) — the regression-safety centrepiece.

Given two registry states (typically a git ref vs the working tree) and the golden
persona set, this runs every persona through both and reports, per lender, exactly
what a rate-card change does to the funnel: how many borrowers' decisions flipped,
how their max sanction moved (average/median delta and the largest movers), and
how many had their binding constraint change. The output is Markdown so CI can
post it as a pull-request comment.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sanctioned.emi import round_rupees
from sanctioned.engine import match
from sanctioned.registry import Registry
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.result import EligibilityResult

_MAX_MOVERS = 5


@dataclass(frozen=True)
class Mover:
    """A persona whose sanction moved the most for a given lender."""

    persona_index: int
    base_sanction: Decimal
    head_sanction: Decimal

    @property
    def delta(self) -> Decimal:
        return self.head_sanction - self.base_sanction


@dataclass(frozen=True)
class LenderDiff:
    """The impact of the change on a single lender across all personas."""

    lender_id: str
    personas: int
    decision_flips: int
    flip_breakdown: dict[str, int]
    sanction_changed: int
    avg_delta: Decimal
    median_delta: Decimal
    binding_changes: int
    largest_movers: tuple[Mover, ...]
    status: str  # "changed", "unchanged", "added", or "removed"


@dataclass(frozen=True)
class DiffReport:
    """The full cross-lender impact report."""

    persona_count: int
    lender_diffs: tuple[LenderDiff, ...]

    @property
    def total_decision_flips(self) -> int:
        return sum(diff.decision_flips for diff in self.lender_diffs)

    @property
    def has_changes(self) -> bool:
        return any(diff.status != "unchanged" for diff in self.lender_diffs)


def _results_by_lender(
    profile: BorrowerProfile, registry: Registry
) -> dict[str, EligibilityResult]:
    return {item.lender_id: item for item in match(profile, registry).results}


def _lender_diff(
    lender_id: str,
    base_results: list[EligibilityResult | None],
    head_results: list[EligibilityResult | None],
) -> LenderDiff:
    flips: Counter[str] = Counter()
    deltas: list[Decimal] = []
    movers: list[Mover] = []
    binding_changes = 0
    decision_flips = 0

    for index, (base, head) in enumerate(zip(base_results, head_results, strict=True)):
        if base is None or head is None:
            continue
        if base.decision is not head.decision:
            decision_flips += 1
            flips[f"{base.decision.value}->{head.decision.value}"] += 1
        if base.max_sanction != head.max_sanction:
            deltas.append(head.max_sanction - base.max_sanction)
            movers.append(Mover(index, base.max_sanction, head.max_sanction))
        if base.binding_constraint is not head.binding_constraint:
            binding_changes += 1

    movers.sort(key=lambda m: abs(m.delta), reverse=True)
    avg = round_rupees(Decimal(sum(deltas)) / len(deltas)) if deltas else Decimal(0)
    median = round_rupees(Decimal(statistics.median(deltas))) if deltas else Decimal(0)
    status = "changed" if (decision_flips or deltas or binding_changes) else "unchanged"

    return LenderDiff(
        lender_id=lender_id,
        personas=sum(1 for b in base_results if b is not None),
        decision_flips=decision_flips,
        flip_breakdown=dict(flips),
        sanction_changed=len(deltas),
        avg_delta=avg,
        median_delta=median,
        binding_changes=binding_changes,
        largest_movers=tuple(movers[:_MAX_MOVERS]),
        status=status,
    )


def diff_registries(
    base: Registry, head: Registry, personas: Sequence[BorrowerProfile]
) -> DiffReport:
    """Compare two registries over a persona set and summarise the impact per lender."""
    base_runs = [_results_by_lender(p, base) for p in personas]
    head_runs = [_results_by_lender(p, head) for p in personas]
    lender_ids = sorted({p.lender_id for p in base} | {p.lender_id for p in head})

    diffs: list[LenderDiff] = []
    for lender_id in lender_ids:
        in_base = any(lender_id in run for run in base_runs)
        in_head = any(lender_id in run for run in head_runs)
        base_results = [run.get(lender_id) for run in base_runs]
        head_results = [run.get(lender_id) for run in head_runs]

        if in_base and not in_head:
            diffs.append(_empty_diff(lender_id, len(personas), "removed"))
        elif in_head and not in_base:
            diffs.append(_empty_diff(lender_id, len(personas), "added"))
        else:
            diffs.append(_lender_diff(lender_id, base_results, head_results))

    return DiffReport(persona_count=len(personas), lender_diffs=tuple(diffs))


def _empty_diff(lender_id: str, personas: int, status: str) -> LenderDiff:
    return LenderDiff(
        lender_id=lender_id,
        personas=personas,
        decision_flips=0,
        flip_breakdown={},
        sanction_changed=0,
        avg_delta=Decimal(0),
        median_delta=Decimal(0),
        binding_changes=0,
        largest_movers=(),
        status=status,
    )


def render_markdown(report: DiffReport) -> str:
    """Render the impact report as Markdown suitable for a PR comment."""
    lines = ["## Policy-diff impact report", ""]
    lines.append(f"Ran **{report.persona_count}** golden personas through both registry states.")
    lines.append("")
    if not report.has_changes:
        lines.append("✅ **No matching impact** — every persona's outcome is unchanged.")
        return "\n".join(lines) + "\n"

    lines.append(f"⚠️ **{report.total_decision_flips}** decision flip(s) across the panel.")
    lines.append("")
    lines.append("| Lender | Status | Flips | Sanctions Δ | Avg Δ | Median Δ | Binding Δ |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for diff in report.lender_diffs:
        lines.append(
            f"| `{diff.lender_id}` | {diff.status} | {diff.decision_flips} | "
            f"{diff.sanction_changed} | {_money(diff.avg_delta)} | "
            f"{_money(diff.median_delta)} | {diff.binding_changes} |"
        )
    lines.append("")

    for diff in report.lender_diffs:
        if diff.status != "changed":
            continue
        lines += _lender_detail(diff)
    return "\n".join(lines) + "\n"


def _lender_detail(diff: LenderDiff) -> list[str]:
    lines = [f"### `{diff.lender_id}`", ""]
    if diff.flip_breakdown:
        breakdown = ", ".join(
            f"{name}: {count}" for name, count in sorted(diff.flip_breakdown.items())
        )
        lines.append(f"- Decision flips — {breakdown}")
    if diff.largest_movers:
        lines.append("- Largest sanction movers:")
        for mover in diff.largest_movers:
            lines.append(
                f"  - persona #{mover.persona_index}: "
                f"{_money(mover.base_sanction)} → {_money(mover.head_sanction)} "
                f"({_signed(mover.delta)})"
            )
    lines.append("")
    return lines


def _money(amount: Decimal) -> str:
    return f"₹{amount:,.0f}"


def _signed(amount: Decimal) -> str:
    sign = "+" if amount >= 0 else "-"
    return f"{sign}₹{abs(amount):,.0f}"

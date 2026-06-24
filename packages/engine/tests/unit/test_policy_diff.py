"""Unit tests for the policy-diff impact report."""

from __future__ import annotations

import shutil
from pathlib import Path

from sanctioned.policy_diff import diff_registries, render_markdown
from sanctioned.registry import Registry, load_registry
from sanctioned.samples import generate_personas

_PERSONAS = generate_personas(limit=80)


def _registry_copy(policies_dir: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    for yaml_file in policies_dir.glob("*.yaml"):
        shutil.copy(yaml_file, dest / yaml_file.name)
    return dest


class TestDiffRegistries:
    def test_identical_registries_have_no_changes(self, registry: Registry) -> None:
        report = diff_registries(registry, registry, _PERSONAS)
        assert not report.has_changes
        assert all(diff.status == "unchanged" for diff in report.lender_diffs)

    def test_tightening_a_policy_is_detected(self, policies_dir: Path, tmp_path: Path) -> None:
        head_dir = _registry_copy(policies_dir, tmp_path / "head")
        # Tighten PSU: cut every FOIR cap, which shrinks FOIR-bound sanctions.
        psu = (head_dir / "psu_bank.yaml").read_text(encoding="utf-8")
        psu = psu.replace("cap_pct: 50", "cap_pct: 40").replace("cap_pct: 55", "cap_pct: 45")
        (head_dir / "psu_bank.yaml").write_text(psu, encoding="utf-8")

        base = load_registry(policies_dir)
        head = load_registry(head_dir)
        report = diff_registries(base, head, _PERSONAS)

        assert report.has_changes
        psu_diff = next(d for d in report.lender_diffs if d.lender_id == "psu_bank")
        assert psu_diff.status == "changed"
        assert psu_diff.sanction_changed > 0
        # Tightening FOIR can only reduce sanctions: average delta is negative.
        assert psu_diff.avg_delta < 0
        # Untouched lenders are unchanged.
        nbfc_diff = next(d for d in report.lender_diffs if d.lender_id == "nbfc")
        assert nbfc_diff.status == "unchanged"

    def test_removed_lender_is_flagged(self, policies_dir: Path, tmp_path: Path) -> None:
        head_dir = _registry_copy(policies_dir, tmp_path / "head")
        (head_dir / "nbfc.yaml").unlink()

        report = diff_registries(load_registry(policies_dir), load_registry(head_dir), _PERSONAS)
        nbfc_diff = next(d for d in report.lender_diffs if d.lender_id == "nbfc")
        assert nbfc_diff.status == "removed"


class TestRenderMarkdown:
    def test_no_change_message(self, registry: Registry) -> None:
        markdown = render_markdown(diff_registries(registry, registry, _PERSONAS))
        assert "No matching impact" in markdown

    def test_change_table_present(self, policies_dir: Path, tmp_path: Path) -> None:
        head_dir = _registry_copy(policies_dir, tmp_path / "head")
        psu = (head_dir / "psu_bank.yaml").read_text(encoding="utf-8")
        (head_dir / "psu_bank.yaml").write_text(
            psu.replace("cap_pct: 55", "cap_pct: 45"), encoding="utf-8"
        )
        report = diff_registries(load_registry(policies_dir), load_registry(head_dir), _PERSONAS)
        markdown = render_markdown(report)
        assert "Policy-diff impact report" in markdown
        assert "psu_bank" in markdown
        assert "Largest sanction movers" in markdown

"""CLI: generate the policy-diff impact report between two registry states.

Each of --base/--head may be either a directory of policy YAML or a git ref
(e.g. HEAD~1). Git refs are materialised by extracting the policies subpath from
that ref. The Markdown report is printed and, optionally, written to --out — which
is how CI posts it as a pull-request comment.

Usage:
    uv run python scripts/policy_diff_report.py --base HEAD~1 --head .
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from sanctioned.policy_diff import diff_registries, render_markdown
from sanctioned.registry import Registry, load_registry
from sanctioned.samples import generate_personas

_DEFAULT_SUBPATH = "packages/engine/policies"


def _has_policy_files(directory: Path) -> bool:
    return any(directory.glob("*.yaml")) or any(directory.glob("*.yml"))


def _load_from_git_ref(ref: str, subpath: str) -> Registry:
    """Extract the policies subpath from a git ref into a temp dir and load it."""
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, subpath],
        capture_output=True,
        text=True,
        check=True,
    )
    paths = [line for line in listing.stdout.splitlines() if line.endswith((".yaml", ".yml"))]
    if not paths:
        raise SystemExit(f"No policy files found at {subpath} in ref '{ref}'")

    tmp_dir = Path(tempfile.mkdtemp(prefix="policy-diff-"))
    for path in paths:
        content = subprocess.run(
            ["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=True
        )
        (tmp_dir / Path(path).name).write_text(content.stdout, encoding="utf-8")
    return load_registry(tmp_dir)


def resolve_registry(source: str, subpath: str) -> Registry:
    """Load a registry from a directory or a git ref."""
    candidate = Path(source)
    if candidate.is_dir():
        policies_dir = candidate if _has_policy_files(candidate) else candidate / subpath
        return load_registry(policies_dir)
    return _load_from_git_ref(source, subpath)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a policy-diff impact report.")
    parser.add_argument("--base", required=True, help="Base registry: a directory or git ref.")
    parser.add_argument("--head", required=True, help="Head registry: a directory or git ref.")
    parser.add_argument(
        "--subpath", default=_DEFAULT_SUBPATH, help="Policies path within a git ref."
    )
    parser.add_argument("--out", type=Path, default=None, help="Optional path to write the report.")
    args = parser.parse_args(argv)

    base = resolve_registry(args.base, args.subpath)
    head = resolve_registry(args.head, args.subpath)
    report = diff_registries(base, head, generate_personas())
    markdown = render_markdown(report)

    print(markdown)
    if args.out is not None:
        args.out.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

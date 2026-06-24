# sanctioned

> Lender-policy eligibility & matching engine for Indian home loans — deterministic,
> explainable, and wrapped in a regression-safety QA harness.

Given a borrower profile, `sanctioned` computes **which lenders will fund them, the maximum
sanction per lender, the indicative rate, and a structured reason trace for every decision** —
with no ML and no probabilistic scoring. The explainability *is* the product.

> [!IMPORTANT]
> All lender numbers in this repository are **indicative, public-sourced approximations**.
> They are never presented as any lender's live or internal policy. Every policy file carries a
> `source` and a `disclaimer`, and every figure's origin is recorded in
> [`docs/data-sources.md`](docs/data-sources.md).

## Why it exists

Hiring demonstrator for **Nestara** (digital home-loan marketplace) targeting an Automation
Engineer / internal-product-expert role. The differentiator is "lender-policy intelligence":
accurate, auditable matching across a large lender panel, plus the regression tooling that lets
policy data change fast without breaking the funnel.

## Architecture at a glance

- **`packages/engine`** — the only home of business rules. Pure typed functions over Pydantic v2
  models; money math in `Decimal`. Lenders are declarative, versioned YAML validated on load.
- **QA harness** — golden-snapshot tests, Hypothesis property invariants, Pandera data validation,
  and a policy-diff impact report ("who flipped and by how much").
- **API / dashboard / copilot** (later phases) — thin consumers of the engine. No rule logic lives
  outside `packages/engine`.

## Quickstart

```bash
uv sync                                 # install the workspace
uv run pytest                           # run the test suite
uv run ruff check && uv run mypy        # lint + strict type-check
```

See [`CLAUDE.md`](CLAUDE.md) for the full build spec and phase plan.

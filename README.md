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

A `uv` + `pnpm` monorepo. Business rules live in exactly one place; everything else consumes them.

- **`packages/engine`** (`sanctioned`) — the only home of business rules. Pure typed functions over
  Pydantic v2 models; money math in `Decimal`. Three products (new loan, balance transfer, top-up).
  Lenders are declarative, versioned YAML validated on load.
- **QA harness** — golden-snapshot tests (360 personas), Hypothesis property invariants (10),
  Pandera feed validation, and a policy-diff impact report ("who flipped and by how much").
- **`packages/api`** (`sanctioned_api`) — FastAPI: `/match`, `/lenders`, `/policy-diff`,
  `/validate`, `/ingest/sandbox`. No rule logic; engine imported as a library.
- **`apps/dashboard`** — Next.js ops UI: borrower form → ranked match grid → reason-trace audit
  ledger; lender policy dossiers; interactive policy-diff. Playwright E2E.
- **`packages/copilot`** (`sanctioned_copilot`) — RAG over policies + runbook, answering only from
  retrieved sources with citations. Offline TF-IDF default; Gemini backend when a key is present.
- **`packages/ingest`** (`sanctioned_ingest`) — sandbox Account-Aggregator ingestion: bank
  statement → derived income/obligations → profile autofill. Setu-pluggable, no real data.

## Quickstart

```bash
uv sync                                 # install the Python workspace
uv run pytest                           # full test suite (engine + api + copilot + ingest)
uv run ruff check && uv run mypy        # lint + strict type-check

# Run the stack locally
uv run uvicorn sanctioned_api.main:app --reload          # API on :8000
cd apps/dashboard && pnpm install && pnpm dev            # dashboard on :3000
pnpm --filter . exec playwright test                     # E2E (from apps/dashboard)

uv run python -m sanctioned                               # engine CLI demo
uv run python scripts/seed_copilot.py                     # copilot demo (set GEMINI_API_KEY for live)
uv run python scripts/policy_diff_report.py --base HEAD --head .   # policy-diff
```

See [`CLAUDE.md`](CLAUDE.md) for the full build spec and phase plan, and
[`docs/deploy.md`](docs/deploy.md) for deploying the API (Fly/Railway) and dashboard (Vercel).

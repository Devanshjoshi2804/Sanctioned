<div align="center">

<img src="docs/assets/logo.svg" width="84" alt="sanctioned logo" />

# sanctioned

### A lender-matching engine that explains every decision.

[![CI](https://github.com/Devanshjoshi2804/Sanctioned/actions/workflows/ci.yml/badge.svg)](https://github.com/Devanshjoshi2804/Sanctioned/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy-lang.org/)

Given a borrower, it computes **which lenders will fund them, the maximum sanction, the indicative
rate, and the binding constraint** — deterministically, with no ML — and returns a **line-by-line
reason trace for every verdict.**

[Quickstart](#quickstart) · [Features](#features) · [Walkthrough](#walkthrough) · [How it works](#how-it-works) · [Architecture](#architecture) · [Testing](#quality--testing)

</div>

<p align="center">
  <img src="docs/assets/hero.png" width="860" alt="sanctioned match grid: ranked lenders with verdict, max sanction, rate, EMI, and an expanded line-by-line reason trace" />
</p>
<p align="center"><sub><i>The match grid — ranked lenders with verdict, max sanction, rate, and the expanded reason trace for one lender.</i></sub></p>

> **Why this exists.** Anyone can wire up a loan calculator. The hard, valuable problem in a
> home-loan marketplace is **lender-policy intelligence**: matching a borrower across a large panel
> *accurately*, *explaining* every yes/no, and changing rate cards *without breaking the funnel*.
> sanctioned treats **explainability and regression-safety as the core engineering problem** — every
> decision carries an auditable reason trace, and every policy change produces a machine-readable
> "who flipped and by how much" report.

## Features

- **Deterministic & explainable** — pure typed rules, no ML. The same borrower always yields the
  same verdict; each lender returns a reason trace naming the rule, the borrower's value, and the threshold.
- **Exact money math** — `Decimal` end to end (EMI / present-value), rounded to whole rupees only at output.
- **Three products** — new home loan, balance transfer (with indicative savings), and top-up (combined-LTV).
- **Policy-as-code** — each lender is a versioned, declarative YAML validated on load; four indicative
  archetypes (PSU bank, private bank, HFC, NBFC).
- **Regression safety** — a 360-persona golden dataset, ten Hypothesis property invariants, Pandera feed
  validation, and a policy-diff impact report CI posts on any policy change.
- **REST API + ops dashboard** — FastAPI over the engine; a Next.js dashboard with the match grid,
  reason-trace ledger, lender dossiers, and an interactive policy-diff explorer.
- **AI copilot** — retrieval-grounded Q&A over the policies and runbook, answering **only from sources,
  with citations** — it cannot invent a rate or a rule.
- **Consent-based ingestion** — pull income and obligations from a bank statement over the Account
  Aggregator framework (Setu), then autofill the borrower.

> [!IMPORTANT]
> **Data accuracy & honesty.** Every lender number is an **indicative, public-sourced
> approximation** — never any lender's live or internal policy. Each policy file carries a `source`
> and a `disclaimer`, and every figure's origin is recorded in
> [`docs/data-sources.md`](docs/data-sources.md). No accuracy metric is fabricated.

## Walkthrough

### Overview — every capability at a glance

The landing page frames what the system does and puts the **AI copilot** front and centre:
retrieval-grounded, cited answers — never from model memory.

<p align="center">
  <img src="docs/assets/overview.png" width="820" alt="Overview page: hero, panel stats (4 lenders, 3 products, 360 golden personas, 10 invariants), an AI-copilot highlight band with an example Q&A, and a capabilities grid" />
</p>

### Regression-safe rate cards — the policy-diff impact report

Shift a lender's terms and replay **all 360 golden personas** through both versions. The report shows
who flips, how sanctions move (average / median Δ and the largest movers), and which constraint starts
binding — so a rate-card change ships without surprises.

<p align="center">
  <img src="docs/assets/demo-policydiff.png" width="820" alt="Policy-diff: shifting one lender's LTV replays 360 personas and reports sanction deltas and binding changes per lender" />
</p>

### AI copilot — grounded, with citations

Ask in plain English. The copilot retrieves from the lender policies and the ops runbook and answers
**only from what it retrieved, with the sources cited** — so it can't hallucinate a rate or a rule.
Offline retrieval by default; Google Gemini embeddings + synthesis when a key is configured.

<p align="center">
  <img src="docs/assets/demo-copilot.png" width="820" alt="Ops copilot answering 'which lenders accept self-employed with two years of ITR?' with a grounded answer and source citations" />
</p>

### Policy-as-code — the lender dossier

Each lender is declarative, versioned YAML validated on load. The dossier renders the policy with its
**provenance**, LTV bands, and CIBIL tiers — every figure traceable to its source.

<p align="center">
  <img src="docs/assets/lender.png" width="820" alt="Lender dossier: provenance, key terms, LTV bands, and CIBIL tiers with decisions and rates" />
</p>

## How it works

For each lender, the engine runs the qualifying gates (property, self-employed, minimum income,
CIBIL, age/tenure), derives the indicative rate, then sizes the loan as the **smallest of three
bounds** — FOIR, LTV (self-consistent band), and the NMI multiplier — against the lender cap. The
smallest one is reported as the **binding constraint**. Every gate and bound emits a reason trace,
in evaluation order, and the panel is ranked eligible-first, then by sanction, then by rate.

## Architecture

A `uv` (Python) + `pnpm` (JavaScript) monorepo. Business rules live in exactly one place; every
other component is a thin consumer.

```
packages/
  engine/      sanctioned          — the only home of business rules (schemas, rules, products,
                                      registry, validation, policy-diff, golden personas)
  api/         sanctioned_api       — FastAPI service over the engine
  copilot/     sanctioned_copilot   — retrieval-augmented ops copilot (offline + Gemini backends)
  ingest/      sanctioned_ingest    — Account-Aggregator ingestion (Setu client + mock)
apps/
  dashboard/                        — Next.js ops UI (Tailwind), Playwright E2E
docs/                               — domain reference, runbook, data provenance, deploy, spec
```

| Layer | Choice |
|---|---|
| Engine | Python 3.12 · Pydantic v2 · `Decimal` |
| Quality | Hypothesis · pytest golden/unit · Pandera |
| API | FastAPI + Uvicorn |
| Dashboard | Next.js 14 (App Router) + Tailwind |
| E2E | Playwright |
| Copilot | Retrieval-augmented (offline TF-IDF or Google Gemini) |
| Ingestion | Setu Account Aggregator (sandbox) |
| Tooling | uv · pnpm · ruff · black · mypy `--strict` · GitHub Actions |

## Quickstart

```bash
uv sync                                          # install the Python workspace

# Run the stack
uv run uvicorn sanctioned_api.main:app --reload  # API + OpenAPI docs on :8000
cd apps/dashboard && pnpm install && pnpm dev     # dashboard on :3000

# CLIs
uv run python -m sanctioned                        # engine demo (prints a ranked MatchResult)
uv run python scripts/seed_copilot.py              # copilot demo (set GEMINI_API_KEY for live LLM)
uv run python scripts/policy_diff_report.py --base HEAD --head .   # policy-diff impact report
```

Everything runs without any API keys — the copilot falls back to offline retrieval and AA ingestion
to a labelled mock. See [`.env.example`](.env.example) for the optional Gemini / Setu configuration.

## Quality & testing

```bash
uv run pytest                                      # unit · integration · property · golden · API
uv run ruff check && uv run black --check .         # lint + format
uv run mypy                                         # strict static typing
cd apps/dashboard && pnpm test:e2e                  # Playwright end-to-end
```

`mypy --strict` across every package, `ruff` and `black` clean, and GitHub Actions runs lint,
type-check, the full suite, and the policy-diff PR comment on every push.

## Guardrails

- No ML or probabilistic scoring anywhere — deterministic rules only.
- No business rule outside the engine package; API, UI, and copilot consume it.
- No `float` for money — `Decimal` end to end.
- Every policy number traceable in `docs/data-sources.md`; every policy file carries a `source` and a `disclaimer`.
- Reason traces are a mandatory part of the output, not optional.

## Documentation

- [`docs/SPEC.md`](docs/SPEC.md) — the full build specification
- [`docs/data-sources.md`](docs/data-sources.md) — provenance for every policy figure
- [`docs/runbook.md`](docs/runbook.md) — ops procedures, FAQ, and the copilot's knowledge base
- [`docs/integrations.md`](docs/integrations.md) — the Gemini copilot and the Setu AA flow
- [`docs/deploy.md`](docs/deploy.md) — deploying the API and dashboard

## License

[MIT](LICENSE).

---

<sub>All lender figures herein are indicative, public-sourced approximations for demonstration only,
and must not be relied upon for an actual lending decision.</sub>

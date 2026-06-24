# Sanctioned

**A deterministic, explainable lender-policy eligibility & matching engine for Indian home loans —
with a regression-safety QA harness, a REST API, an ops dashboard, a retrieval-grounded copilot,
and consent-based Account-Aggregator ingestion.**

Given a borrower profile, Sanctioned computes **which lenders will fund them, the maximum sanction
per lender, the indicative rate, the binding constraint, and a structured reason trace for every
decision** — deterministically, with no machine learning. The explainability is the product.

> [!IMPORTANT]
> **Data accuracy & honesty.** Every lender number in this repository is an **indicative,
> public-sourced approximation** — never any lender's live, internal, or guaranteed policy. Each
> policy file carries a `source` and a `disclaimer`, and every figure's origin is recorded in
> [`docs/data-sources.md`](docs/data-sources.md). No accuracy or benchmark metric is fabricated.

---

## Why it exists

A home-loan marketplace lives or dies on **lender-policy intelligence**: accurately matching
borrowers to a large panel of lenders, and being able to change rate cards quickly without
breaking the funnel. Sanctioned is a production-grade reference implementation of exactly that —
deterministic matching, full auditability, and the regression tooling to ship policy changes
safely.

---

## Features

### Matching engine (the core)
- **Deterministic & explainable.** Pure typed rules — no ML, no probabilistic scoring. The same
  borrower always produces the same verdict.
- **Reason trace for every decision.** Each lender returns a line-by-line audit trail: the rule,
  the borrower's value, the policy threshold, pass/fail. The "why didn't this customer match?"
  answer, rendered verbatim in the UI.
- **Exact money math.** `Decimal` end to end — EMI and present-value-of-annuity formulas, rounded
  to whole rupees only at output. Never `float` for currency.
- **Three products.** New home loan, balance transfer (with indicative monthly savings), and
  top-up (combined-LTV) — one rule engine dispatched per product.
- **Policy-as-code.** Each lender's eligibility policy is a versioned, declarative YAML validated
  against a strict schema on load; the engine logic is generic and lenders differ only in data.
- **Four indicative lender archetypes** spanning the market: public-sector bank, private bank,
  housing finance company, and NBFC.

### Quality & regression safety
- **Golden dataset** of 360 synthetic personas with snapshot tests that fail on any behavioural
  drift.
- **Property-based invariants** (Hypothesis) — ten economic guarantees (monotonic income/CIBIL/
  obligations, LTV/FOIR/tenure/min-loan ceilings, co-applicant non-negativity, determinism, and
  reason-trace completeness) checked across the full input space.
- **Data validation** (Pandera) — persona and lender-offer feeds checked for impossible values
  (non-positive income, out-of-range CIBIL, FOIR > 100, LTV > 90, missing rates).
- **Policy-diff impact report** — change a lender's terms and replay all 360 personas through both
  versions: who flips, how sanctions move (avg/median Δ and the largest movers), and which
  constraint starts binding. CI posts this as a pull-request comment on any policy change.

### Service & interface
- **REST API** (FastAPI) — `/match`, `/lenders`, `/lenders/{id}`, `/policy-diff`, `/validate`,
  `/ask`, `/ingest/sandbox`, with auto-served OpenAPI docs. No business logic lives in the API.
- **Ops dashboard** (Next.js) — a borrower form → ranked match grid → expandable reason-trace
  ledger; lender policy dossiers with provenance; an interactive policy-diff explorer; and the
  copilot. End-to-end tested with Playwright.

### AI copilot (retrieval-augmented)
- **Grounded question answering** over the lender policies and the ops runbook. Answers cite the
  exact sources they were drawn from and **never** draw on the model's own knowledge, so it cannot
  invent a rate or a rule.
- **Provider-agnostic** — a dependency-free offline retriever by default; Google Gemini embeddings
  and synthesis when an API key is configured.

### Consent-based ingestion
- **Account Aggregator (Setu) integration** — pull a borrower's income and obligations from a bank
  statement over India's AA framework (consent → data session → fetch), then autofill the profile.
  Real consent flow against the Setu sandbox; a labelled mock statement is the offline fallback.

---

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
docs/                               — domain reference, ops runbook, data provenance, deploy, integrations
scripts/                            — persona generator, policy-diff report, copilot seed
```

## Tech stack

| Layer | Choice |
|---|---|
| Engine | Python 3.12, Pydantic v2, `Decimal` money math |
| Property tests | Hypothesis · **Golden/unit** pytest · **Data validation** Pandera |
| API | FastAPI + Uvicorn |
| Dashboard | Next.js 14 (App Router) + Tailwind CSS |
| E2E | Playwright |
| Copilot | Retrieval-augmented (offline TF-IDF or Google Gemini) |
| Ingestion | Setu Account Aggregator (sandbox) |
| Tooling | uv, pnpm, ruff, black, mypy `--strict`, GitHub Actions |

---

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

Configuration is via environment variables — see [`.env.example`](.env.example). Everything runs
without any keys (the copilot falls back to offline retrieval; AA ingestion falls back to the mock).

---

## Quality & testing

```bash
uv run pytest                                      # 132 tests: unit, integration, property, golden, API
uv run ruff check && uv run black --check .         # lint + format
uv run mypy                                         # strict static typing
cd apps/dashboard && pnpm test:e2e                  # 8 Playwright end-to-end specs
```

- **`mypy --strict`** across every package, **ruff** and **black** clean.
- **GitHub Actions** runs lint, type-check, the full test suite, and the policy-diff PR comment.

---

## Guardrails (enforced)

- No ML and no probabilistic scoring anywhere — deterministic rules only.
- No business rule outside the engine package; the API, UI, and copilot consume it.
- No `float` for money — `Decimal` end to end.
- Every policy number is traceable in `docs/data-sources.md`; every policy file carries a `source`
  and a `disclaimer`.
- Reason traces are a mandatory part of the output, not optional.

## Documentation

- [`docs/data-sources.md`](docs/data-sources.md) — provenance for every policy figure
- [`docs/runbook.md`](docs/runbook.md) — ops procedures, FAQ, and the copilot's knowledge base
- [`docs/integrations.md`](docs/integrations.md) — the Gemini copilot and the Setu AA flow
- [`docs/deploy.md`](docs/deploy.md) — deploying the API and dashboard
- [`docs/SPEC.md`](docs/SPEC.md) — the full build specification

---

_All lender figures herein are indicative, public-sourced approximations for demonstration only,
and must not be relied upon for an actual lending decision._

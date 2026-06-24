# CLAUDE.md — `sanctioned`

> Lender-Policy Eligibility & Matching Engine + QA harness for Indian home loans.
> Build spec for Claude Code. Read this fully before writing code. Follow the **phase plan** (bottom) — each phase must be green and demoable before starting the next.
>
> _If you want to keep the auto-loaded `CLAUDE.md` lean later, move §4–§9 into `docs/SPEC.md` and leave a one-line pointer here. For now this single file is the source of truth._

---

## 1. What this is and why it exists

A standalone, production-grade system that, given a borrower profile, computes **which of N lenders will fund them, the max sanction per lender, the indicative rate, and a structured reason trace for every decision** — deterministically, with no ML.

It is wrapped in a **QA/regression harness** (golden dataset, property-based invariants, policy-diff impact reports, data-validation) and a thin **ops dashboard + copilot** so non-engineers can self-serve.

This is built as a hiring demonstrator for **Nestara** (digital home-loan marketplace: new loan / balance transfer / top-up / refinance; core IP = "lender-policy intelligence" + accurate matching across a large lender panel). The role it targets is **Automation Engineer / internal product expert**: automation, E2E tests for loan/BT/matching journeys, regression safety, data-validation, internal dashboards, L1 support tooling. **Design every decision to map to that role.**

### Design principles (non-negotiable)
- **Deterministic & explainable.** Pure typed functions. No ML, no probabilistic scoring. Every output carries a `reasons[]` trace. The explainability *is* the product.
- **Policy-as-code.** Each lender's eligibility policy is a versioned, declarative YAML validated against a strict schema. Logic is generic; lenders differ only in data.
- **Regression-first.** A policy change must produce a machine-readable "who flipped and by how much" report. Releases move fast without breaking matching.
- **Honest data.** All lender numbers are **indicative, public-sourced approximations** — never claimed as any lender's live/internal policy. Every policy file carries a `source` + `disclaimer`. Do **not** invent precision or fabricate accuracy metrics.

---

## 2. Tech stack (use exactly these unless a phase says otherwise)

| Layer | Choice | Notes |
|---|---|---|
| Engine core | **Python 3.12**, **Pydantic v2** | schemas, rules, orchestrator |
| Money math | pure Python `Decimal` | no float for currency |
| Property tests | **Hypothesis** | invariants |
| Data validation | **Pandera** | policy + persona feed validation |
| Unit/golden tests | **pytest** | golden-file snapshots |
| API | **FastAPI** + uvicorn | one language with engine; (NestJS gateway optional later) |
| Dashboard | **Next.js 14 (App Router)** + **Tailwind** + shadcn/ui | ops-facing |
| E2E | **Playwright** | new-loan / BT / matching journeys |
| Copilot (Phase 4) | Pydantic AI + OpenAI embeddings + a local vector store (FAISS/Chroma) | RAG over policy registry + runbook |
| AA ingestion (Phase 5) | Setu **sandbox** | mock bank-statement → profile autofill |
| Package mgmt | **uv** (Python), **pnpm** (JS) | |
| CI | **GitHub Actions** | golden + property + policy-diff + lint |
| Deploy | Vercel (dashboard), Railway/Fly (API) | ship a live link |

Conventions: `ruff` + `black` + `mypy --strict` for Python; `eslint` + `prettier` for JS. Commit style: Conventional Commits. Every public function typed and docstring'd. No business rule may live in the API or UI layer — rules live only in `engine`.

---

## 3. Repository layout

```
sanctioned/
├── CLAUDE.md                      # this file
├── README.md                      # public-facing: what/why/live-demo/screenshots
├── docs/
│   ├── domain.md                  # lending math reference (mirror of §5)
│   ├── runbook.md                 # ops runbook + FAQ (feeds copilot)
│   └── data-sources.md            # provenance for every policy number
├── pyproject.toml                 # uv workspace
├── packages/
│   ├── engine/
│   │   ├── sanctioned/
│   │   │   ├── schemas/           # policy.py, borrower.py, result.py
│   │   │   ├── rules/             # foir.py ltv.py multiplier.py age_tenure.py
│   │   │   │                      # cibil.py employer.py self_employed.py property_.py
│   │   │   ├── products/          # new_loan.py balance_transfer.py top_up.py
│   │   │   ├── emi.py             # EMI / PV-of-annuity (Decimal)
│   │   │   ├── registry.py        # load + version policies from YAML
│   │   │   ├── engine.py          # orchestrator: profile × registry -> MatchResult
│   │   │   ├── policy_diff.py     # old registry vs new -> impact report
│   │   │   └── validation/        # policy_validator.py, feed_validator.py (pandera)
│   │   ├── policies/              # <lender_id>.yaml  (versioned)
│   │   ├── data/personas/         # golden personas (json/yaml)
│   │   └── tests/
│   │       ├── unit/              # per-rule
│   │       ├── golden/            # persona -> expected snapshot
│   │       ├── property/          # hypothesis invariants
│   │       └── conftest.py
│   └── copilot/                   # Phase 4
├── apps/
│   └── dashboard/                 # Next.js
│       ├── app/                   # /  (match grid),  /lender/[id], /policy-diff
│       ├── components/
│       └── e2e/                   # playwright: new_loan.spec, bt.spec, matching.spec
├── scripts/
│   ├── generate_personas.py       # synthetic persona generator
│   ├── policy_diff_report.py      # CLI -> markdown report (used by CI)
│   └── seed_copilot.py
└── .github/workflows/ci.yml
```

---

## 4. Core data models (Pydantic v2)

Spell these out in `packages/engine/sanctioned/schemas/`. Use `Decimal` for money/rates, enums for closed sets, and `model_config = ConfigDict(frozen=True)` where inputs should be immutable.

### 4.1 Enums
```python
EmploymentType   = SALARIED | SELF_EMPLOYED_PROFESSIONAL | SELF_EMPLOYED_BUSINESS
ProductType      = NEW_HOME_LOAN | BALANCE_TRANSFER | TOP_UP
LenderType       = PUBLIC_BANK | PRIVATE_BANK | HFC | NBFC
PropertyType     = APPROVED_RESALE | UNDER_CONSTRUCTION | NEW_FROM_BUILDER | PLOT_PLUS_CONSTRUCTION | SELF_CONSTRUCTION
CityTier         = METRO | TIER_1 | TIER_2 | TIER_3
Decision         = APPROVE | REFER | REJECT
Constraint       = FOIR | LTV | NMI_MULTIPLIER | LENDER_MAX_CAP | TENURE
EmployerCategory = SUPER_CAT | CAT_A | CAT_B | CAT_C | UNCATEGORIZED   # SUPER_CAT = PSU/listed-MNC etc.
```

### 4.2 `BorrowerProfile`
```
applicant:
  age: int
  employment_type: EmploymentType
  net_monthly_income: Decimal          # take-home (post-tax/EPF), NOT CTC
  variable_monthly_income: Decimal = 0 # trailing-24m avg bonus/incentive, monthly
  cibil: int                            # 300..900
  employer_category: EmployerCategory = UNCATEGORIZED
  business_vintage_years: Decimal = 0   # for self-employed
  itr_years_available: int = 0          # for self-employed
co_applicants: list[CoApplicant] = []   # each: income, cibil, employment_type, is_co_owner
existing_monthly_obligations: Decimal   # sum of current EMIs + cc min-due
property:
  value: Decimal
  type: PropertyType
  city_tier: CityTier
loan_request:
  product_type: ProductType
  requested_amount: Decimal | None
  requested_tenure_years: int
  existing_loan_outstanding: Decimal = 0 # BT / TOP_UP
  existing_rate_pct: Decimal | None = 0  # BT (to compute savings)
```

### 4.3 `LenderPolicy` (the YAML schema)
```
lender_id: str            # slug, matches filename
lender_name: str
lender_type: LenderType
policy_version: str       # semver; bump on any change
effective_date: date
source: str               # URL / doc reference
disclaimer: str           # required: "indicative, public-sourced ..."
products: [ProductType]   # which products this policy supports

age:
  salaried:      { min_entry: int, max_at_maturity: int }
  self_employed: { min_entry: int, max_at_maturity: int }
tenure: { max_years: int }

foir:                      # ordered bands by net monthly income; first match wins
  salaried:      [ { up_to_nmi: Decimal|null, cap_pct: Decimal } ]
  self_employed: [ { up_to_nmi: Decimal|null, cap_pct: Decimal } ]

nmi_multiplier: { min: Decimal, max: Decimal }   # max loan ≈ multiplier × net monthly income

ltv_bands:                 # RBI-aligned, lender may be tighter; first match by loan amount
  - { up_to_amount: 3000000,  max_ltv_pct: 90 }
  - { up_to_amount: 7500000,  max_ltv_pct: 80 }
  - { up_to_amount: null,     max_ltv_pct: 75 }

min_income:                # net monthly
  salaried:      { metro: Decimal, non_metro: Decimal }
  self_employed: { metro: Decimal, non_metro: Decimal }   # use monthly net profit

cibil_tiers:               # ordered; first matching band wins
  - { min_score: 800, max_score: 900, decision: APPROVE, rate_pct: 8.10 }
  - { min_score: 750, max_score: 799, decision: APPROVE, rate_pct: 8.40 }
  - { min_score: 700, max_score: 749, decision: APPROVE, rate_pct: 8.90 }
  - { min_score: 650, max_score: 699, decision: REFER,   rate_pct: 9.75 }
  - { min_score: 300, max_score: 649, decision: REJECT,  rate_pct: null }
  - { min_score: -1,  max_score: -1,  decision: REFER,   rate_pct: 9.75 }  # thin/no file

self_employed:
  min_business_vintage_years: Decimal
  itr_years_required: int

property_rules:            # per-type allow + optional overrides
  - { type: UNDER_CONSTRUCTION, allowed: true,  ltv_override_pct: 80, tenure_override_years: null }
  - { type: PLOT_PLUS_CONSTRUCTION, allowed: true, ltv_override_pct: 70 }
  # types absent from list default to allowed:true, no override

variable_pay_haircut_pct: 50          # % of variable income counted

employer_category_perks:              # optional
  - { category: SUPER_CAT, foir_bonus_pct: 5, rate_discount_bps: 10 }
  - { category: CAT_A,     foir_bonus_pct: 2, rate_discount_bps: 5 }

co_applicant: { allowed: true, combine_income: true, max_count: 2 }

product_overrides:                    # optional per-product tweaks
  BALANCE_TRANSFER: { max_ltv_pct: 80, min_seasoning_months: 12 }
  TOP_UP:           { combined_max_ltv_pct: 75 }

limits: { min_loan: 500000, max_loan: 100000000 }
```

### 4.4 `EligibilityResult` (per lender) and `MatchResult`
```
EligibilityResult:
  lender_id, lender_name
  decision: Decision
  eligible: bool
  max_sanction: Decimal
  binding_constraint: Constraint | null
  indicative_rate_pct: Decimal | null
  indicative_emi: Decimal | null
  bounds: { foir: Decimal, ltv: Decimal, multiplier: Decimal, lender_cap: Decimal }
  effective_tenure_years: int
  reasons: [ ReasonTrace ]
  warnings: [ str ]
  # BT/top-up only:
  monthly_saving: Decimal | null
  net_benefit_note: str | null

ReasonTrace:
  code: str          # e.g. "CIBIL_FLOOR", "FOIR_CAP", "LTV_CAP", "AGE_MAX", "MIN_INCOME"
  rule: str          # human label
  passed: bool
  value: str         # borrower's value
  threshold: str     # policy threshold
  detail: str        # one-line explanation

MatchResult:
  borrower: BorrowerProfile
  generated_at: datetime
  results: [ EligibilityResult ]   # sorted: eligible desc, max_sanction desc, rate asc
  summary: { eligible_count, best_rate, max_sanction_overall, top_lender_id }
```

---

## 5. Domain logic (implement exactly — this is the lending math)

All amounts `Decimal`, rounded to whole rupees at output only. Rate inputs are annual %.

### 5.1 Income
- `assessed_income = net_monthly_income + (variable_monthly_income × variable_pay_haircut_pct/100)`
- With co-applicants and `combine_income`: sum assessed incomes of co-owner co-applicants.
- Self-employed: `net_monthly_income` is monthly net profit from ITR; require `business_vintage_years ≥ min_business_vintage_years` and `itr_years_available ≥ itr_years_required`, else REJECT (`SE_VINTAGE` / `SE_ITR`).

### 5.2 EMI / max-principal (use these formulas)
Let `r = annual_rate / 12 / 100`, `n = tenure_months`.
- `EMI(P) = P·r·(1+r)^n / ((1+r)^n − 1)`
- `MaxPrincipal(EMI) = EMI · (1 − (1+r)^(−n)) / r`
- If `r == 0`, `MaxPrincipal = EMI · n`.

### 5.3 Effective tenure
`effective_tenure_years = min(policy.tenure.max_years, max_at_maturity − applicant.age)` using the age block for the applicant's employment type. If `≤ 0` → REJECT (`AGE_MAX`). Use the **youngest** applicant's runway when co-applicants present (most lenders allow this).

### 5.4 The three bounds, then take the min
1. **FOIR bound.** Pick `cap_pct` from the first income band ≥ assessed income (null `up_to_nmi` = catch-all). Add `employer_category_perks.foir_bonus_pct` if applicable (cap total at a sane ceiling, e.g. 65%). `available_emi = assessed_income × cap_pct/100 − existing_monthly_obligations`. If `available_emi ≤ 0` → REJECT (`FOIR_NO_HEADROOM`). `foir_bound = MaxPrincipal(available_emi)` at the applicable tier rate over effective tenure.
2. **LTV bound.** Pick `max_ltv` from `ltv_bands` by **the loan amount band**, applying any `property_rules.ltv_override_pct` and product overrides. `ltv_bound = property.value × max_ltv/100`. (Note the band is keyed off loan amount; iterate/solve so the chosen band is self-consistent — start from highest band, step down.)
3. **Multiplier bound.** `multiplier_bound = nmi_multiplier.max × assessed_income`.

`max_sanction = min(foir_bound, ltv_bound, multiplier_bound, limits.max_loan)`, floored at 0. `binding_constraint` = whichever produced the min. If `max_sanction < limits.min_loan` → REJECT (`BELOW_MIN_LOAN`).

### 5.5 Rate & decision
- Pick `cibil_tiers` band by score (`-1`/thin-file → the `min_score:-1` row). `decision` from that band; apply `rate_discount_bps`. If band decision is REJECT or below lender's effective CIBIL floor → REJECT (`CIBIL_FLOOR`).
- `min_income` check by employment type × metro/non-metro (METRO/TIER_1 → metro figure). Fail → REJECT (`MIN_INCOME`).
- `property_rules.allowed == false` for the type → REJECT (`PROPERTY_TYPE`).
- Final `decision`: REJECT if any hard rule failed; REFER if CIBIL band is REFER or only soft warnings; else APPROVE.

### 5.6 Products
- **NEW_HOME_LOAN**: as above; `requested_amount` optional (if given, also report whether it fits).
- **BALANCE_TRANSFER**: loan amount = `existing_loan_outstanding`. Re-run eligibility on it. Apply BT `max_ltv` / `min_seasoning_months` overrides. `monthly_saving = EMI(outstanding@existing_rate) − EMI(outstanding@new_rate)` over remaining tenure; add `net_benefit_note` flagging processing/foreclosure friction as a warning, not a hard fail.
- **TOP_UP**: `combined = existing_loan_outstanding + requested_amount`. Enforce `combined ≤ property.value × combined_max_ltv_pct/100` (`TOPUP_LTV`) and FOIR on the **combined** EMI.

### 5.7 Reason traces
Emit a `ReasonTrace` for **every** evaluated rule (passed and failed), in evaluation order. The dashboard renders these verbatim — they are the explainability deliverable. Always populate `value` and `threshold`.

---

## 6. Validation layer (Pandera) — maps to JD "data validation scripts"

`validation/policy_validator.py`: on registry load, assert per policy — `foir.*.cap_pct ∈ (0,70]`, `ltv_bands` monotonic & `≤ 90`, `cibil_tiers` cover 300–900 with no gaps/overlaps and are ordered, `age.max_at_maturity > min_entry`, `min_loan < max_loan`, rates present for non-REJECT tiers, `source`+`disclaimer` non-empty. Fail loud with the offending `lender_id` + field.

`validation/feed_validator.py` (Pandera schemas): validate borrower-persona feeds and any lender-offer feed for inconsistencies — negative/zero income, CIBIL out of 300–900, FOIR cap > 100, LTV > 90, missing rate tier, property value ≤ 0. Produce a `validation_report.md`.

---

## 7. Policy-diff impact report — the killer ops feature

`policy_diff.py` + `scripts/policy_diff_report.py`:
- Input: two registry states (git `HEAD~1` vs working tree, or two dirs) + the golden persona set.
- Run all personas through both. Output **markdown**: per lender, count of personas whose `decision` flipped, whose `max_sanction` changed (with avg/median Δ and the largest movers), and whose `binding_constraint` changed.
- CI posts this as a PR comment whenever any file under `packages/engine/policies/` changes. This answers "what does this rate-card change do to our funnel?" — lead the README/Loom with it.

---

## 8. Tests

### 8.1 Golden (`tests/golden/`)
≥ 300 personas (hand-verified seeds + `scripts/generate_personas.py` synthetic spread across employment types, CIBIL tiers, metro/non-metro, property bands, co-applicant cases, all 3 products). Each persona has an expected `MatchResult` snapshot. `pytest` fails on any drift; update snapshots only via an explicit `--update-golden` flag.

### 8.2 Property-based invariants (`tests/property/`, Hypothesis)
Generate valid random borrowers + policies and assert (each its own test):
1. **Monotonic income** — increasing `net_monthly_income` never decreases `max_sanction` (ceteris paribus).
2. **LTV ceiling** — `max_sanction ≤ property.value × highest_applicable_ltv` always.
3. **FOIR ceiling** — implied new EMI ≤ `assessed_income × cap_pct/100 − existing_obligations + ε`.
4. **Co-applicant non-negative** — adding an earning co-owner never decreases `max_sanction`.
5. **CIBIL monotonic** — lowering CIBIL never adds an APPROVE lender.
6. **Obligation monotonic** — increasing `existing_monthly_obligations` never increases `max_sanction`.
7. **Tenure bound** — `effective_tenure_years ≤ policy.tenure.max_years` and matures before `max_at_maturity`.
8. **Determinism** — same input → identical output across runs/orderings.
9. **Min-loan floor** — APPROVE ⇒ `max_sanction ≥ limits.min_loan`.
10. **Reason completeness** — every result has ≥1 trace per evaluated rule; REJECT always has ≥1 failed trace.

### 8.3 Unit (`tests/unit/`)
Per rule + EMI/PV math (assert against known worked examples, e.g. ₹80k net, 50% FOIR, 8.5%/20y → EMI cap ~₹40k → ~₹46–48L). Cover band-boundary edges.

### 8.4 E2E (`apps/dashboard/e2e/`, Playwright)
Three specs matching the JD verbatim: `new_loan.spec`, `bt.spec`, `matching.spec`. Drive synthetic personas through the dashboard, assert the match grid + reason traces render and key numbers match the engine.

---

## 9. API + Dashboard + Copilot + AA

### 9.1 API (FastAPI)
- `POST /match` → `BorrowerProfile` → `MatchResult`.
- `GET /lenders`, `GET /lenders/{id}` → policy (with provenance).
- `POST /policy-diff` → two registry refs → impact report JSON.
- `POST /validate` → run feed validation.
OpenAPI auto-served. Engine imported as a library — **no rule logic in the API**.

### 9.2 Dashboard (Next.js, ops-facing)
- `/` — borrower form → **match grid**: lenders ranked, max sanction, rate, EMI, binding constraint, eligible/refer/reject badge. Expand any row → full reason-trace list ("why didn't this customer match HDFC?").
- `/lender/[id]` — rendered policy + provenance.
- `/policy-diff` — upload/select two versions → impact report.
Clean, dense, internal-tool aesthetic (consult the frontend-design skill before building UI). No client-side rule logic.

### 9.3 Copilot (Phase 4)
RAG over `packages/engine/policies/*` + `docs/runbook.md` + `docs/domain.md`. Answers ops/sales questions ("which lenders fund self-employed with 2-yr ITR in a tier-2 town?") with **citations to the source policy/section**. Pydantic AI + embeddings + FAISS/Chroma. Never answer rule questions from the model's own knowledge — only from retrieved policy/engine output.

### 9.4 AA ingestion (Phase 5, stretch)
Setu **sandbox** only: mock consent → mock bank statement → derive `net_monthly_income`, `existing_monthly_obligations`, salary-credit regularity → autofill `BorrowerProfile`. Demonstrates the consent-first / document-fetch angle. Clearly labelled sandbox; no real data.

---

## 10. Seed lender policies (build these first as templates)

Create ≥ 4 in `packages/engine/policies/`, each with honest `source`/`disclaimer`. Use **indicative, public-sourced** numbers — do not present as any lender's actual internal policy. Suggested seeds spanning the archetypes:

- `psu_bank.yaml` — PSU bank archetype: FOIR 50–60% by slab, NMI×60, conservative LTV, CIBIL floor 700, low rates, wide property acceptance.
- `private_bank.yaml` — private bank: FOIR 50–55%, faster on salaried super-cat employers, rate discounts for SUPER_CAT/CAT_A.
- `hfc.yaml` — housing finance co: friendlier to self-employed (lower vintage, higher SE FOIR), slightly higher rates.
- `nbfc.yaml` — NBFC: accepts CIBIL 650–699 (REFER) at higher rate, tighter LTV, supports thin-file (`-1`).

Each must validate, parse into `LenderPolicy`, and appear in the golden run. Record every number's origin in `docs/data-sources.md`.

---

## 11. Guardrails (repeat — enforce in code review)
- No ML / no probabilistic scoring anywhere. Deterministic rules only.
- No business rule outside `engine`. API/UI/copilot consume it.
- No float for money — `Decimal` end to end.
- Every policy number traceable in `docs/data-sources.md`; every policy file carries `source` + `disclaimer`.
- README and copy say **"indicative, public-sourced"** — never claim live/internal lender accuracy, never invent accuracy/benchmark metrics.
- Reason traces are mandatory output, not optional.

---

## 12. Commands
```
uv sync                                   # install engine
uv run pytest                             # all python tests
uv run pytest packages/engine/tests/property   # invariants only
uv run python scripts/policy_diff_report.py --base HEAD~1 --head .   # diff report
uv run python scripts/generate_personas.py --n 300
uv run uvicorn sanctioned_api.main:app --reload
pnpm --filter dashboard dev               # ops dashboard
pnpm --filter dashboard exec playwright test
```

---

## 13. Phase plan (build in order; each ends green + demoable)

**Phase 0 — Skeleton.** uv workspace, `pyproject`, all schema files, enums, `emi.py` with unit tests, `psu_bank.yaml` parsing into `LenderPolicy`, `registry.py`, `policy_validator.py`. DoD: `uv run pytest tests/unit` green; one policy loads & validates.

**Phase 1 — Engine + matching.** All rules in `rules/`, `products/new_loan.py`, `engine.py` orchestrator, 4 seed policies, NEW_HOME_LOAN end-to-end with full reason traces. Golden dataset (≥300) + golden tests. DoD: `uv run pytest` green; CLI prints a MatchResult for a sample borrower.

**Phase 2 — QA harness.** Hypothesis invariants (all 10), Pandera feed validation, `policy_diff.py` + report script, GitHub Actions CI (lint + mypy + pytest + property + policy-diff PR comment). DoD: CI green on a PR; editing a policy YAML produces an impact-report comment.

**Phase 3 — BT + Top-up + API + Dashboard + E2E.** `balance_transfer.py`, `top_up.py`; FastAPI; Next.js match grid + reason traces + `/policy-diff`; Playwright specs for the 3 journeys. Deploy dashboard (Vercel) + API (Railway). DoD: live URL; Playwright green.

**Phase 4 — Copilot + runbook.** `docs/runbook.md` + FAQ, RAG copilot with citations. DoD: copilot answers 5 seeded ops questions with correct policy citations.

**Phase 5 — AA ingestion (stretch).** Setu sandbox profile autofill. DoD: sandbox statement → autofilled borrower → match grid.

Stop and ask me before adding scope beyond a phase's DoD. Keep Phases 0–2 airtight before any UI polish — the engine + harness are the whole differentiator.

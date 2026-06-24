# Policy data sources & provenance

Every numeric value in every policy under `packages/engine/policies/` must be traceable here.
All figures are **indicative, public-sourced approximations** — never any lender's live or
internal policy.

## How to read this file

Each lender section records, per policy area, the public source consulted and any modelling
assumptions made to fill gaps. When a precise public figure is unavailable, the value is an
honest archetype estimate and is marked as such — we do **not** invent precision.

---

## `psu_bank.yaml` — Public-sector bank archetype

Indicative profile modelled on publicly published PSU home-loan terms (conservative LTV, low
headline rates, CIBIL-led pricing, FOIR by income slab). None of these figures are taken from any
lender's live or internal systems; gaps are filled with conservative archetype estimates and
marked as such.

| Policy area | Value(s) | Source / basis |
|---|---|---|
| Entry / maturity age | Salaried 21–60, self-employed 21–70 | Typical public-sector bank home-loan eligibility ranges as published in public product pages and Most Important Terms & Conditions (MITC) documents. |
| Max tenure | 30 years | Common published PSU maximum for home loans. |
| FOIR by income slab | 50% (≤₹50k), 55% (≤₹1L), 60% (>₹1L) | Archetype estimate; PSU lenders publicly indicate FOIR/NMI norms rising with income. Conservative relative to private peers. |
| NMI multiplier | 50×–60× net monthly income | Archetype estimate consistent with PSU loan-to-income norms; not a published exact figure. |
| LTV slabs | ≤₹30L: 90%, ≤₹75L: 80%, >₹75L: 75% | RBI LTV ceilings for housing loans (90/80/75 by amount band); top band held conservative. |
| Min net monthly income | Salaried ₹25k metro / ₹18k non-metro; self-employed ₹30k / ₹22k | Archetype estimate; PSU minimum-income norms are not uniformly published. |
| CIBIL bands & rates | 800+: 8.10%, 750–799: 8.40%, 700–749: 8.90%, <700: reject, thin-file: refer @ 9.75% | Indicative spread reflecting publicly advertised CIBIL-linked home-loan card rates and a 700 floor; exact basis points are illustrative. |
| Self-employed gates | ≥3 years vintage, 3 ITR years | Common PSU documentation requirement (typically 2–3 years ITR/business proof). |
| Property LTV overrides | Under-construction 80%, plot+construction 75% | Conservative archetype reflecting tighter LTV on non-ready properties. |
| Variable-pay haircut | 50% counted | Standard underwriting haircut on variable income; archetype value. |
| Employer perks | SUPER_CAT +5% FOIR / −10 bps; CAT_A +2% / −5 bps | Illustrative concessions for premier employer categories; not a published schedule. |
| Loan limits | ₹5,00,000 – ₹10,00,00,000 | Archetype min/max consistent with PSU home-loan ticket sizes. |
| BT / top-up overrides | BT LTV 80%, seasoning 12 months; top-up combined LTV 75% | Archetype values consistent with common balance-transfer/top-up norms. |

---

## `private_bank.yaml` — Private bank archetype

Indicative profile modelled on publicly published private-bank home-loan terms: tighter CIBIL
floor (720 for full approval, 700–719 on refer), employer-category-driven pricing with the
richest discounts of the panel, and higher minimum incomes. Figures are illustrative archetype
estimates, not any lender's published schedule.

| Policy area | Value(s) | Source / basis |
|---|---|---|
| Entry / maturity age | Salaried 23–65, self-employed 25–70 | Typical private-bank eligibility windows. |
| FOIR | 50% (≤₹75k), 55% (>₹75k) | Archetype; private banks publicly indicate tighter FOIR than HFCs. |
| NMI multiplier | 55×–72× | Archetype estimate. |
| LTV slabs | 90 / 80 / 75 by RBI amount band | RBI LTV ceilings. |
| CIBIL bands & rates | 800+: 8.35%, 750–799: 8.55%, 720–749: 8.85%, 700–719: refer @ 9.40%, <700 & thin-file: reject | Illustrative CIBIL-linked card rates; private banks typically decline thin files. |
| Employer perks | SUPER_CAT +5%/−15bps, CAT_A +3%/−10bps, CAT_B +1%/−5bps | Illustrative premier-employer concessions. |
| Loan limits | ₹10,00,000 – ₹15,00,00,000 | Archetype ticket-size range. |

---

## `hfc.yaml` — Housing Finance Company archetype

Indicative profile modelled on publicly published HFC characteristics: self-employed-friendly
underwriting (2-year vintage, higher SE FOIR, 60% variable-pay counted, thin-file refer) at
higher rates than banks.

| Policy area | Value(s) | Source / basis |
|---|---|---|
| Entry / maturity age | Salaried 21–65, self-employed 21–70 | Typical HFC eligibility windows. |
| FOIR | Salaried 50/55%, self-employed 55/60% | Archetype; HFCs publicly position as more SE-accommodating. |
| Self-employed gates | 2-year vintage, 2 ITR years | Friendlier than bank norms. |
| Variable-pay haircut | 60% counted | More generous than the 50% bank archetype. |
| CIBIL bands & rates | 800+: 8.75%, 750–799: 9.10%, 700–749: 9.50%, 650–699: refer @ 10.25%, thin-file: refer @ 10.75% | Illustrative; higher than bank rates. |
| Loan limits | ₹3,00,000 – ₹7,50,00,000 | Archetype ticket-size range. |

---

## `nbfc.yaml` — NBFC archetype

Indicative profile modelled on publicly published NBFC characteristics: the widest credit box
(CIBIL 650–699 and thin files accepted on refer) at the highest rates and tightest LTV.

| Policy area | Value(s) | Source / basis |
|---|---|---|
| Tenure | Max 25 years | Tighter than the 30-year bank/HFC archetype. |
| LTV slabs | 85 / 75 / 70 by amount band | Conservative relative to RBI ceilings, reflecting NBFC risk appetite. |
| Self-employed gates | 2-year vintage, 1 ITR year | Most lenient of the panel. |
| CIBIL bands & rates | 800+: 9.25%, 750–799: 9.60%, 700–749: 10.10%, 650–699: refer @ 10.90%, thin-file: refer @ 11.50% | Illustrative; highest rates of the panel, widest acceptance. |
| Loan limits | ₹2,00,000 – ₹5,00,00,000 | Archetype ticket-size range. |

---

> All four archetypes deliberately span the lender landscape (PSU → private → HFC → NBFC) so the
> matching engine and policy-diff tooling exercise a realistic spread of outcomes.

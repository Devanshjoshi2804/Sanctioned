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

> Additional lenders (`private_bank`, `hfc`, `nbfc`) are added in Phase 1.

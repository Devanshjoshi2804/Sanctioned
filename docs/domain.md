# Lending domain reference

Authoritative reference for the lending math implemented in `packages/engine`. This mirrors
§5 of [`SPEC.md`](SPEC.md); when the two disagree, `SPEC.md` wins until this file is
reconciled. Filled in alongside the engine implementation (Phase 1).

## Glossary

- **FOIR** — Fixed Obligations to Income Ratio. The share of assessed monthly income a lender will
  let go toward all EMIs (existing obligations + the proposed loan).
- **LTV** — Loan to Value. Maximum loan as a percentage of property value; RBI-aligned, lenders may
  be tighter.
- **NMI multiplier** — a cap on the loan as a multiple of Net Monthly Income.
- **Assessed income** — net monthly income plus a haircut-adjusted share of variable pay, summed
  across co-owner co-applicants where the policy allows.
- **Binding constraint** — whichever of the FOIR / LTV / multiplier / lender-cap bounds produced the
  final (minimum) sanction.

> To be expanded with worked examples during Phase 1.

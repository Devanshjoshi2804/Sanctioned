# Ops runbook & FAQ

Operational reference for non-engineers using the matching engine and dashboard,
and the explanatory corpus the copilot retrieves over. Each section is
self-contained so it can be cited on its own. Figures are **indicative,
public-sourced** — see [`data-sources.md`](data-sources.md).

## Decisions: approve, refer, reject

Every lender returns one of three verdicts. **Approve** means the borrower clears
all hard rules and the credit band approves. **Refer** means the file is fundable
but needs manual review — typically a borderline CIBIL band, a thin credit file,
or a balance transfer the lender can only partly fund. **Reject** means a hard
rule failed: below the CIBIL floor, below minimum income, no FOIR headroom, an
unfunded property type, an exhausted age runway, or an amount below the lender's
minimum loan size. A rejection always carries at least one failed reason trace
explaining which rule blocked it.

## FOIR — fixed obligations to income ratio

FOIR is the share of assessed monthly income a lender will allow toward all EMIs.
The engine takes the FOIR cap for the borrower's income band, adds any employer
bonus (capped at a 65% ceiling), subtracts existing obligations, and treats the
remaining headroom as the EMI the new loan may carry. The present value of that
EMI stream over the effective tenure is the FOIR-bound sanction. If existing
obligations consume the whole allowance, the file is rejected for no headroom.

## LTV — loan-to-value caps

LTV caps the loan as a percentage of property value, in RBI-aligned slabs that
tighten as the loan grows (commonly 90% up to ₹30L, 80% up to ₹75L, 75% above).
Under-construction and plot-plus-construction properties usually carry a tighter
LTV override. Because the slab depends on the loan amount itself, the engine
solves for the self-consistent band.

## NMI multiplier

The net-monthly-income multiplier caps the loan at a fixed multiple of assessed
income (roughly 50–72× across the panel). It is one of the three bounds; the
smallest of FOIR, LTV, and multiplier (and the lender's absolute cap) becomes the
max sanction, and that smallest one is reported as the binding constraint.

## CIBIL bands and indicative rates

Each lender prices by CIBIL band. Prime files (800+) get the lowest rate; the rate
rises as the score falls until the lender's floor, below which the file is
rejected. The public-sector archetype is cheapest for prime borrowers (around
8.10%); the NBFC archetype is the most expensive but the most accommodating. A
thin or absent credit file (encoded as CIBIL −1) is handled by a dedicated band:
the PSU, HFC, and NBFC archetypes refer thin files, while the private-bank
archetype declines them.

## Self-employed underwriting

Self-employed applicants must clear a business-vintage and an ITR-history gate.
The housing-finance and NBFC archetypes are the most accommodating — two years of
vintage (NBFC needs only one ITR year) — while banks expect three. Self-employed
income is the monthly net profit from ITRs, and the HFC archetype also allows a
higher FOIR and counts more variable income.

## Balance transfer

A balance transfer re-underwrites the outstanding loan at the new lender's terms.
The engine sizes the lender's capacity, checks whether it covers the outstanding
(referring when it only partly does), and estimates the monthly saving from the
rate change. The saving is indicative and should be weighed against processing and
foreclosure charges before transferring.

## Top-up

A top-up adds borrowing on top of an existing loan. Eligibility is assessed on the
combined exposure: the combined amount must fit a dedicated combined-LTV cap and
the FOIR headroom must service the combined EMI. The reported figure is the
additional amount available beyond the outstanding.

## Property types

Resale and builder properties are widely accepted. Under-construction,
plot-plus-construction, and self-construction are accepted by most archetypes but
at a tighter LTV. A lender that does not fund a property type rejects the file with
a property-type trace.

## Lender panel

Four indicative archetypes span the market: a **public-sector bank** (cheapest,
conservative LTV, CIBIL floor 700), a **private bank** (employer-led pricing,
higher CIBIL floor, declines thin files), a **housing finance company**
(self-employed-friendly, higher rates), and an **NBFC** (widest credit box
including sub-prime refers and thin files, highest rates, tightest LTV).

## FAQ

**Which lenders fund self-employed borrowers with only two years of ITR?** The HFC
archetype (two-year vintage, two ITR years) and the NBFC archetype (two-year
vintage, one ITR year). The bank archetypes expect three years.

**Who offers the lowest rate for a prime borrower?** The public-sector bank
archetype, at around 8.10% for scores of 800+.

**Which lenders consider applicants with no credit history?** The PSU, HFC, and
NBFC archetypes refer thin files (CIBIL −1) at a higher rate; the private bank
declines them.

**What is the maximum LTV on a high-value property?** On loans above ₹75 lakh the
top LTV slab applies — 75% at the bank/HFC archetypes and 70% at the NBFC.

**Why was a customer rejected?** Open the customer's row in the match grid and read
the reason trace: the failed line names the exact rule — CIBIL floor, minimum
income, FOIR headroom, property type, age runway, or minimum loan size.

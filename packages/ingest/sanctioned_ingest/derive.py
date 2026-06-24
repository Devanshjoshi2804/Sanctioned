"""Derive borrower financials from a bank statement.

Net monthly income is the median of monthly salary credits; existing obligations
are the median of monthly EMI debits; salary regularity is the share of observed
months that carry a salary credit. Medians (not means) keep one-off spikes from
skewing the figures.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from statistics import median

from sanctioned.emi import round_rupees
from sanctioned_ingest.statement import BankStatement, TxnCategory

_SANDBOX_DISCLAIMER = (
    "Derived from a sandbox/mock bank statement for demonstration only — "
    "not real account data and not a verified income assessment."
)
_REGULAR_THRESHOLD = Decimal("0.8")


@dataclass(frozen=True)
class DerivedFinancials:
    """Financial fields inferred from a statement, plus a confidence read."""

    net_monthly_income: Decimal
    existing_monthly_obligations: Decimal
    salary_regularity: str  # REGULAR | IRREGULAR | INSUFFICIENT
    regularity_score: Decimal  # 0..1
    months_observed: int
    source: str
    disclaimer: str


def _monthly_totals(
    statement: BankStatement, category: TxnCategory, *, credits: bool
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for txn in statement.transactions:
        if txn.category is not category:
            continue
        if credits and txn.amount <= 0:
            continue
        if not credits and txn.amount >= 0:
            continue
        totals[txn.txn_date.strftime("%Y-%m")] += abs(txn.amount)
    return dict(totals)


def derive_financials(
    statement: BankStatement, *, source: str = "SETU_SANDBOX_MOCK"
) -> DerivedFinancials:
    """Infer income, obligations, and salary regularity from a statement."""
    months = statement.months()
    month_count = len(months)

    salary_by_month = _monthly_totals(statement, TxnCategory.SALARY, credits=True)
    emi_by_month = _monthly_totals(statement, TxnCategory.EMI, credits=False)

    net_income = (
        round_rupees(Decimal(median(salary_by_month.values()))) if salary_by_month else Decimal(0)
    )
    obligations = (
        round_rupees(Decimal(median(emi_by_month.values()))) if emi_by_month else Decimal(0)
    )

    salary_months = len(salary_by_month)
    score = Decimal(salary_months) / Decimal(month_count) if month_count else Decimal(0)
    score = score.quantize(Decimal("0.01"))

    if month_count < 2 or not salary_by_month:
        regularity = "INSUFFICIENT"
    elif score >= _REGULAR_THRESHOLD:
        regularity = "REGULAR"
    else:
        regularity = "IRREGULAR"

    return DerivedFinancials(
        net_monthly_income=net_income,
        existing_monthly_obligations=obligations,
        salary_regularity=regularity,
        regularity_score=score,
        months_observed=month_count,
        source=source,
        disclaimer=_SANDBOX_DISCLAIMER,
    )

"""Bank-statement models.

A minimal, AA-shaped representation: a statement is a list of categorised
transactions over a period. Amounts are signed Decimals (positive = credit,
negative = debit). These mirror the fields an Account-Aggregator FIP would return
for a deposit account.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TxnCategory(StrEnum):
    """Coarse transaction categories used to derive financials."""

    SALARY = "SALARY"
    EMI = "EMI"
    OTHER_CREDIT = "OTHER_CREDIT"
    OTHER_DEBIT = "OTHER_DEBIT"


class BankTransaction(BaseModel):
    """A single statement line."""

    model_config = ConfigDict(frozen=True)

    txn_date: date
    amount: Decimal  # positive = credit, negative = debit
    description: str
    category: TxnCategory


class BankStatement(BaseModel):
    """A categorised statement for one account over an observation period."""

    model_config = ConfigDict(frozen=True)

    account_ref: str
    transactions: tuple[BankTransaction, ...]

    def months(self) -> list[str]:
        """Distinct ``YYYY-MM`` months present, in order."""
        seen: dict[str, None] = {}
        for txn in self.transactions:
            seen.setdefault(txn.txn_date.strftime("%Y-%m"), None)
        return list(seen)

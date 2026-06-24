"""Statement sources.

``MockStatementSource`` synthesises a deterministic, clearly-labelled sandbox
statement. ``SetuAaSource`` is the seam for the real Setu Account-Aggregator
sandbox — it documents the consent → data-session → fetch flow and the
credentials it would need, but performs no network call here.
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Protocol

from sanctioned_ingest.statement import BankStatement, BankTransaction, TxnCategory


class StatementSource(Protocol):
    """Yields a bank statement for ingestion."""

    def fetch(self) -> BankStatement: ...


def _add_months(year: int, month: int, count: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + count
    return total // 12, total % 12 + 1


class MockStatementSource:
    """A deterministic synthetic statement: a regular salary, a recurring EMI, and
    a little noise, over a handful of months. No randomness — same inputs, same
    statement."""

    def __init__(
        self,
        *,
        monthly_salary: Decimal = Decimal("90000"),
        monthly_emi: Decimal = Decimal("12000"),
        months: int = 4,
        start: tuple[int, int] = (2026, 2),
        skip_salary_month: int | None = None,
    ) -> None:
        self._salary = monthly_salary
        self._emi = monthly_emi
        self._months = months
        self._start = start
        self._skip_salary_month = skip_salary_month

    def fetch(self) -> BankStatement:
        txns: list[BankTransaction] = []
        for index in range(self._months):
            year, month = _add_months(self._start[0], self._start[1], index)
            if index != self._skip_salary_month:
                txns.append(
                    BankTransaction(
                        txn_date=date(year, month, 1),
                        amount=self._salary,
                        description="SALARY CREDIT — ACME CORP",
                        category=TxnCategory.SALARY,
                    )
                )
            txns.append(
                BankTransaction(
                    txn_date=date(year, month, 5),
                    amount=-self._emi,
                    description="ACH EMI — AUTO LOAN",
                    category=TxnCategory.EMI,
                )
            )
            txns.append(
                BankTransaction(
                    txn_date=date(year, month, 18),
                    amount=Decimal("-8500"),
                    description="UPI — GROCERIES",
                    category=TxnCategory.OTHER_DEBIT,
                )
            )
        return BankStatement(account_ref="SANDBOX-XXXX-0000", transactions=tuple(txns))


class SetuAaSource:
    """Seam for the real Setu Account-Aggregator sandbox.

    A production implementation would, using the consent artefacts:
      1. create a consent request and obtain consent (redirect/notification),
      2. open a data session for the consented FIP account,
      3. poll until the FI data is ready, then fetch and decrypt it,
      4. map the returned transactions into :class:`BankStatement`.

    It needs ``SETU_CLIENT_ID`` / ``SETU_CLIENT_SECRET`` (sandbox). This stub is
    intentionally inert so no real data flow can happen by accident.
    """

    def __init__(self) -> None:
        self.client_id = os.environ.get("SETU_CLIENT_ID")
        self.client_secret = os.environ.get("SETU_CLIENT_SECRET")

    def fetch(self) -> BankStatement:
        raise NotImplementedError(
            "Setu AA sandbox integration is not wired up. Set SETU_CLIENT_ID / "
            "SETU_CLIENT_SECRET and implement the consent + data-session flow, or "
            "use MockStatementSource for the demo."
        )

"""Statement sources.

``MockStatementSource`` synthesises a deterministic, clearly-labelled sandbox
statement. ``SetuAaSource`` is the seam for the real Setu Account-Aggregator
sandbox — it documents the consent → data-session → fetch flow and the
credentials it would need, but performs no network call here.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

from sanctioned_ingest.statement import BankStatement, BankTransaction, TxnCategory

if TYPE_CHECKING:
    from sanctioned_ingest.setu import SetuAaClient, SetuConfig


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
    """Statement source backed by the real Setu Account-Aggregator client.

    Fetching requires an **already-approved** consent id (the customer approves the
    consent in their AA app via the web-view URL from
    :meth:`~sanctioned_ingest.setu.SetuAaClient.start_consent`). Credentials come
    from ``SETU_*`` env vars; constructing without them raises, so no real data
    flow can happen by accident.
    """

    def __init__(
        self,
        consent_id: str,
        *,
        config: SetuConfig | None = None,
        client: SetuAaClient | None = None,
        lookback_months: int = 6,
    ) -> None:
        from sanctioned_ingest.setu import SetuAaClient, SetuConfig

        self._consent_id = consent_id
        self._client = client or SetuAaClient(config or SetuConfig.from_env())
        self._to_date = date.today()
        self._from_date = self._to_date - timedelta(days=lookback_months * 30)

    def fetch(self) -> BankStatement:
        return self._client.fetch_statement(
            self._consent_id, from_date=self._from_date, to_date=self._to_date
        )

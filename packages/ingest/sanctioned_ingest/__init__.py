"""Sandbox Account-Aggregator ingestion.

Turns a bank statement into the financial fields of a borrower profile. The
statement source is pluggable (:class:`StatementSource`): a deterministic mock is
provided, and a Setu AA sandbox client fits behind the same seam. Everything here
is explicitly sandbox/demo — no real bank data is fetched or stored.
"""

from sanctioned_ingest.derive import DerivedFinancials, derive_financials
from sanctioned_ingest.source import MockStatementSource, StatementSource
from sanctioned_ingest.statement import BankStatement, BankTransaction, TxnCategory

__all__ = [
    "BankStatement",
    "BankTransaction",
    "DerivedFinancials",
    "MockStatementSource",
    "StatementSource",
    "TxnCategory",
    "derive_financials",
]
__version__ = "0.1.0"

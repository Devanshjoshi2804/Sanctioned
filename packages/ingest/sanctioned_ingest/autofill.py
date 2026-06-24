"""Map derived financials onto borrower-profile form fields."""

from __future__ import annotations

from sanctioned_ingest.derive import DerivedFinancials


def profile_autofill(derived: DerivedFinancials) -> dict[str, str]:
    """The borrower-form fields a statement can pre-fill (income and obligations)."""
    return {
        "net_monthly_income": str(derived.net_monthly_income),
        "existing_monthly_obligations": str(derived.existing_monthly_obligations),
    }

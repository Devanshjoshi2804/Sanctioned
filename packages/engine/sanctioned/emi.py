"""Loan amortisation math — EMI and the present value of an annuity.

All arithmetic is in :class:`~decimal.Decimal`; never ``float``. The two core
functions are exact inverses:

* :func:`emi` — the equated monthly instalment for a given principal.
* :func:`max_principal` — the largest principal an instalment can service (the
  present value of the EMI stream).

Internally we keep full precision and round to whole rupees only at the output
boundary, via :func:`round_rupees` (§5 of the spec).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_ONE = Decimal(1)
_MONTHS_PER_YEAR = Decimal(12)
_PERCENT = Decimal(100)


def monthly_rate(annual_rate_pct: Decimal) -> Decimal:
    """Convert an annual percentage rate to a monthly fraction.

    e.g. ``12`` (% p.a.) -> ``0.01`` per month.
    """
    return annual_rate_pct / _MONTHS_PER_YEAR / _PERCENT


def _require_positive_tenure(tenure_months: int) -> None:
    if tenure_months <= 0:
        raise ValueError(f"tenure_months must be positive, got {tenure_months}")


def emi(principal: Decimal, annual_rate_pct: Decimal, tenure_months: int) -> Decimal:
    """Equated monthly instalment for ``principal`` over ``tenure_months``.

    ``EMI = P*r*(1+r)^n / ((1+r)^n - 1)``; when ``r == 0`` the instalment is the
    principal spread evenly (``P / n``).
    """
    _require_positive_tenure(tenure_months)
    rate = monthly_rate(annual_rate_pct)
    if rate == 0:
        return principal / tenure_months
    growth = (_ONE + rate) ** tenure_months
    return principal * rate * growth / (growth - _ONE)


def max_principal(installment: Decimal, annual_rate_pct: Decimal, tenure_months: int) -> Decimal:
    """Largest principal serviceable by ``installment`` (present value of annuity).

    ``MaxPrincipal = EMI * (1 - (1+r)^(-n)) / r``; when ``r == 0`` it is simply
    ``EMI * n``.
    """
    _require_positive_tenure(tenure_months)
    rate = monthly_rate(annual_rate_pct)
    if rate == 0:
        return installment * tenure_months
    discount = (_ONE + rate) ** (-tenure_months)
    return installment * (_ONE - discount) / rate


def round_rupees(amount: Decimal) -> Decimal:
    """Round a money amount to whole rupees, half-up (the output convention)."""
    return amount.quantize(_ONE, rounding=ROUND_HALF_UP)

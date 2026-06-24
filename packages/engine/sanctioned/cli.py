"""Command-line demo: run a borrower against the bundled lender panel.

Renders the match grid and, for each lender, the full reason trace — the same
explainability the dashboard will show. Run with ``python -m sanctioned``.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from sanctioned.engine import match
from sanctioned.registry import load_registry
from sanctioned.schemas.borrower import (
    Applicant,
    BorrowerProfile,
    LoanRequest,
    Property,
)
from sanctioned.schemas.enums import CityTier, EmploymentType, ProductType, PropertyType
from sanctioned.schemas.result import EligibilityResult, MatchResult

_DEFAULT_POLICIES_DIR = Path(__file__).resolve().parent.parent / "policies"


def _sample_borrower() -> BorrowerProfile:
    """A representative salaried borrower for the demo."""
    return BorrowerProfile(
        applicant=Applicant(
            age=34,
            employment_type=EmploymentType.SALARIED,
            net_monthly_income=Decimal("90000"),
            variable_monthly_income=Decimal("20000"),
            cibil=805,
        ),
        existing_monthly_obligations=Decimal("12000"),
        property=Property(
            value=Decimal("7000000"),
            type=PropertyType.APPROVED_RESALE,
            city_tier=CityTier.METRO,
        ),
        loan_request=LoanRequest(
            product_type=ProductType.NEW_HOME_LOAN,
            requested_tenure_years=20,
        ),
    )


def _money(amount: Decimal) -> str:
    return f"₹{amount:,.0f}"


def _render(result: MatchResult) -> str:
    borrower = result.borrower.applicant
    lines = [
        "=" * 78,
        "MATCH RESULT",
        "=" * 78,
        f"Borrower: age {borrower.age}, {borrower.employment_type.value}, "
        f"net income {_money(borrower.net_monthly_income)}/mo, CIBIL {borrower.cibil}",
        f"Property: {_money(result.borrower.property.value)} "
        f"({result.borrower.property.type.value}, {result.borrower.property.city_tier.value})",
        f"Summary: {result.summary.eligible_count} eligible | "
        f"best rate {result.summary.best_rate or '-'}% | "
        f"top sanction {_money(result.summary.max_sanction_overall)}",
        "-" * 78,
        f"{'LENDER':<22}{'DECISION':<10}{'SANCTION':>14}{'RATE':>8}{'EMI':>12}{'BINDS':>12}",
        "-" * 78,
    ]
    for eligibility in result.results:
        lines.append(_render_row(eligibility))
    lines.append("=" * 78)
    lines.append("REASON TRACES")
    for eligibility in result.results:
        lines.append("-" * 78)
        lines.append(f"{eligibility.lender_name} ({eligibility.decision.value})")
        for trace in eligibility.reasons:
            mark = "PASS" if trace.passed else "FAIL"
            lines.append(f"  [{mark}] {trace.rule}: {trace.detail}")
    return "\n".join(lines)


def _render_row(eligibility: EligibilityResult) -> str:
    rate = f"{eligibility.indicative_rate_pct}%" if eligibility.indicative_rate_pct else "-"
    emi = _money(eligibility.indicative_emi) if eligibility.indicative_emi else "-"
    binds = eligibility.binding_constraint.value if eligibility.binding_constraint else "-"
    return (
        f"{eligibility.lender_name[:21]:<22}"
        f"{eligibility.decision.value:<10}"
        f"{_money(eligibility.max_sanction):>14}"
        f"{rate:>8}"
        f"{emi:>12}"
        f"{binds:>12}"
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point: evaluate the sample borrower and print the match result."""
    parser = argparse.ArgumentParser(description="Run the sanctioned matching demo.")
    parser.add_argument(
        "--policies",
        type=Path,
        default=_DEFAULT_POLICIES_DIR,
        help="Directory of lender policy YAML files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the MatchResult as JSON instead of a rendered table.",
    )
    args = parser.parse_args(argv)

    registry = load_registry(args.policies)
    result = match(_sample_borrower(), registry)

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(_render(result))
    return 0

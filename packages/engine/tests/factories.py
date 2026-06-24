"""Convenience builders for borrower profiles in tests.

A single salaried, metro, prime-credit borrower serves as the baseline; tests
override only the fields they care about. Keeps test bodies focused on the one
variable under examination.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sanctioned.schemas.borrower import (
    Applicant,
    BorrowerProfile,
    CoApplicant,
    LoanRequest,
    Property,
)
from sanctioned.schemas.enums import (
    CityTier,
    EmployerCategory,
    EmploymentType,
    ProductType,
    PropertyType,
)


def make_profile(
    *,
    age: int = 35,
    employment_type: EmploymentType = EmploymentType.SALARIED,
    net_monthly_income: Decimal | str = "80000",
    variable_monthly_income: Decimal | str = "0",
    cibil: int = 800,
    employer_category: EmployerCategory = EmployerCategory.UNCATEGORIZED,
    business_vintage_years: Decimal | str = "0",
    itr_years_available: int = 0,
    existing_monthly_obligations: Decimal | str = "0",
    property_value: Decimal | str = "5000000",
    property_type: PropertyType = PropertyType.APPROVED_RESALE,
    city_tier: CityTier = CityTier.METRO,
    product_type: ProductType = ProductType.NEW_HOME_LOAN,
    requested_amount: Decimal | str | None = None,
    requested_tenure_years: int = 20,
    existing_loan_outstanding: Decimal | str = "0",
    existing_rate_pct: Decimal | str | None = None,
    co_applicants: Sequence[CoApplicant] = (),
) -> BorrowerProfile:
    """Build a borrower profile from a prime-salaried baseline with overrides."""
    return BorrowerProfile(
        applicant=Applicant(
            age=age,
            employment_type=employment_type,
            net_monthly_income=Decimal(net_monthly_income),
            variable_monthly_income=Decimal(variable_monthly_income),
            cibil=cibil,
            employer_category=employer_category,
            business_vintage_years=Decimal(business_vintage_years),
            itr_years_available=itr_years_available,
        ),
        co_applicants=tuple(co_applicants),
        existing_monthly_obligations=Decimal(existing_monthly_obligations),
        property=Property(
            value=Decimal(property_value),
            type=property_type,
            city_tier=city_tier,
        ),
        loan_request=LoanRequest(
            product_type=product_type,
            requested_amount=None if requested_amount is None else Decimal(requested_amount),
            requested_tenure_years=requested_tenure_years,
            existing_loan_outstanding=Decimal(existing_loan_outstanding),
            existing_rate_pct=None if existing_rate_pct is None else Decimal(existing_rate_pct),
        ),
    )


def make_co_owner(
    *,
    net_monthly_income: Decimal | str = "40000",
    cibil: int = 780,
    employment_type: EmploymentType = EmploymentType.SALARIED,
    is_co_owner: bool = True,
    age: int = 32,
) -> CoApplicant:
    """Build a co-applicant, co-owner by default."""
    return CoApplicant(
        net_monthly_income=Decimal(net_monthly_income),
        cibil=cibil,
        employment_type=employment_type,
        is_co_owner=is_co_owner,
        age=age,
    )

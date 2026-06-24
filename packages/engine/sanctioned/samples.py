"""Deterministic synthetic borrower personas for the golden dataset.

The generator is a pure cartesian product over the dimensions that matter for
matching — employment type, credit tier, location, property size, income, and
co-applicant presence — so the same call always yields the same personas in the
same order. That determinism is what makes the golden snapshot stable.
"""

from __future__ import annotations

import itertools
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

_EMPLOYMENT = (
    EmploymentType.SALARIED,
    EmploymentType.SELF_EMPLOYED_PROFESSIONAL,
    EmploymentType.SELF_EMPLOYED_BUSINESS,
)
_CIBIL_SCORES = (810, 760, 720, 690, -1)  # prime, good, fair, sub-prime, thin file
_CITY_TIERS = (CityTier.METRO, CityTier.TIER_2)
_PROPERTY_VALUES = (Decimal("2500000"), Decimal("6000000"))
_INCOMES = (Decimal("40000"), Decimal("90000"), Decimal("160000"))
_CO_OWNER_COUNTS = (0, 1)
_EMPLOYER_CYCLE = (
    EmployerCategory.UNCATEGORIZED,
    EmployerCategory.SUPER_CAT,
    EmployerCategory.CAT_A,
)
_AGE_CYCLE = (32, 45)


def _build_persona(
    index: int,
    employment: EmploymentType,
    cibil: int,
    city: CityTier,
    property_value: Decimal,
    income: Decimal,
    co_owner_count: int,
) -> BorrowerProfile:
    is_self_employed = employment.is_self_employed
    applicant = Applicant(
        age=_AGE_CYCLE[index % len(_AGE_CYCLE)],
        employment_type=employment,
        net_monthly_income=income,
        variable_monthly_income=Decimal(0) if is_self_employed else income / 10,
        cibil=cibil,
        employer_category=(
            EmployerCategory.UNCATEGORIZED
            if is_self_employed
            else _EMPLOYER_CYCLE[index % len(_EMPLOYER_CYCLE)]
        ),
        business_vintage_years=Decimal(5) if is_self_employed else Decimal(0),
        itr_years_available=3 if is_self_employed else 0,
    )
    co_applicants = (
        (
            CoApplicant(
                net_monthly_income=Decimal("40000"),
                cibil=780,
                employment_type=EmploymentType.SALARIED,
                is_co_owner=True,
                age=30,
            ),
        )
        if co_owner_count
        else ()
    )
    return BorrowerProfile(
        applicant=applicant,
        co_applicants=co_applicants,
        existing_monthly_obligations=Decimal("10000") if index % 2 else Decimal(0),
        property=Property(value=property_value, type=PropertyType.APPROVED_RESALE, city_tier=city),
        loan_request=LoanRequest(product_type=ProductType.NEW_HOME_LOAN, requested_tenure_years=20),
    )


def generate_personas(limit: int | None = None) -> tuple[BorrowerProfile, ...]:
    """Generate the deterministic persona spread (360 profiles; optionally capped)."""
    combos = itertools.product(
        _EMPLOYMENT,
        _CIBIL_SCORES,
        _CITY_TIERS,
        _PROPERTY_VALUES,
        _INCOMES,
        _CO_OWNER_COUNTS,
    )
    personas = tuple(_build_persona(index, *combo) for index, combo in enumerate(combos))
    return personas[:limit] if limit is not None else personas

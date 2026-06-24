"""Hypothesis strategies and immutable-mutation helpers for property tests.

Borrower profiles are generated from integer-backed Decimals (never floats) so
money stays exact. Self-employed applicants are given enough vintage/ITR history
to clear those gates, keeping the invariants focused on the sizing logic rather
than on the qualification gates.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import strategies as st

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


def _money(low: int, high: int) -> st.SearchStrategy[Decimal]:
    return st.integers(min_value=low, max_value=high).map(Decimal)


@st.composite
def co_applicants(draw: st.DrawFn, *, max_count: int = 2) -> tuple[CoApplicant, ...]:
    count = draw(st.integers(min_value=0, max_value=max_count))
    result = []
    for _ in range(count):
        result.append(
            CoApplicant(
                net_monthly_income=draw(_money(0, 150000)),
                cibil=draw(st.integers(min_value=300, max_value=900)),
                employment_type=draw(st.sampled_from(list(EmploymentType))),
                is_co_owner=draw(st.booleans()),
                age=draw(st.integers(min_value=21, max_value=60)),
            )
        )
    return tuple(result)


@st.composite
def borrowers(draw: st.DrawFn) -> BorrowerProfile:
    """Generate a valid NEW_HOME_LOAN borrower across the full input space."""
    employment = draw(st.sampled_from(list(EmploymentType)))
    is_self_employed = employment is not EmploymentType.SALARIED
    income = draw(_money(15000, 400000))
    cibil = draw(st.one_of(st.just(-1), st.integers(min_value=300, max_value=900)))

    applicant = Applicant(
        age=draw(st.integers(min_value=21, max_value=62)),
        employment_type=employment,
        net_monthly_income=income,
        variable_monthly_income=draw(_money(0, 100000)),
        cibil=cibil,
        employer_category=draw(st.sampled_from(list(EmployerCategory))),
        business_vintage_years=Decimal(6) if is_self_employed else Decimal(0),
        itr_years_available=4 if is_self_employed else 0,
    )
    return BorrowerProfile(
        applicant=applicant,
        co_applicants=draw(co_applicants()),
        existing_monthly_obligations=draw(_money(0, 120000)),
        property=Property(
            value=draw(_money(1000000, 40000000)),
            type=draw(st.sampled_from(list(PropertyType))),
            city_tier=draw(st.sampled_from(list(CityTier))),
        ),
        loan_request=LoanRequest(
            product_type=ProductType.NEW_HOME_LOAN,
            requested_tenure_years=draw(st.integers(min_value=5, max_value=30)),
        ),
    )


# --- Immutable mutation helpers (frozen models -> build a changed copy) ---


def with_income(profile: BorrowerProfile, value: Decimal) -> BorrowerProfile:
    return profile.model_copy(
        update={"applicant": profile.applicant.model_copy(update={"net_monthly_income": value})}
    )


def with_cibil(profile: BorrowerProfile, value: int) -> BorrowerProfile:
    return profile.model_copy(
        update={"applicant": profile.applicant.model_copy(update={"cibil": value})}
    )


def with_obligations(profile: BorrowerProfile, value: Decimal) -> BorrowerProfile:
    return profile.model_copy(update={"existing_monthly_obligations": value})


def add_co_owner(profile: BorrowerProfile, *, income: Decimal, age: int) -> BorrowerProfile:
    """Append an earning co-owner of the given age (caller controls the runway)."""
    extra = CoApplicant(
        net_monthly_income=income,
        cibil=780,
        employment_type=EmploymentType.SALARIED,
        is_co_owner=True,
        age=age,
    )
    return profile.model_copy(update={"co_applicants": (*profile.co_applicants, extra)})

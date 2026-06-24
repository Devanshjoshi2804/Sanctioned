"""Borrower-side inputs to the matching engine.

These models are immutable (``frozen=True``): a borrower profile is a fact about
the world at evaluation time, and the engine must never mutate its input. All
money and rate fields are :class:`~decimal.Decimal` — never ``float`` — so that
rupee arithmetic is exact.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sanctioned.schemas.enums import (
    CityTier,
    EmployerCategory,
    EmploymentType,
    ProductType,
    PropertyType,
)

# A CIBIL score is in [300, 900]; the sentinel -1 means a thin or absent credit
# file, which lenders handle via a dedicated policy band rather than a number.
THIN_FILE_CIBIL = -1


def _validate_cibil(score: int) -> int:
    """Allow a real score in [300, 900] or the thin-file sentinel (-1)."""
    if score == THIN_FILE_CIBIL or 300 <= score <= 900:
        return score
    raise ValueError(f"cibil must be -1 (thin file) or within 300..900, got {score}")


class CoApplicant(BaseModel):
    """A co-applicant whose income may be combined with the primary applicant's.

    Only co-owners contribute income under most policies; see ``is_co_owner``.
    """

    model_config = ConfigDict(frozen=True)

    net_monthly_income: Decimal = Field(ge=0)
    cibil: int
    employment_type: EmploymentType
    is_co_owner: bool = True
    age: int = Field(ge=18, le=100)

    @model_validator(mode="after")
    def _check_cibil(self) -> CoApplicant:
        _validate_cibil(self.cibil)
        return self


class Applicant(BaseModel):
    """The primary borrower.

    ``net_monthly_income`` is take-home pay (post-tax/EPF), not CTC. For the
    self-employed it is monthly net profit derived from ITRs.
    """

    model_config = ConfigDict(frozen=True)

    age: int = Field(ge=18, le=100)
    employment_type: EmploymentType
    net_monthly_income: Decimal = Field(ge=0)
    # Trailing-24-month average of bonus/incentive, expressed monthly.
    variable_monthly_income: Decimal = Field(default=Decimal(0), ge=0)
    cibil: int
    employer_category: EmployerCategory = EmployerCategory.UNCATEGORIZED
    # Self-employed only; ignored for salaried applicants.
    business_vintage_years: Decimal = Field(default=Decimal(0), ge=0)
    itr_years_available: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check_cibil(self) -> Applicant:
        _validate_cibil(self.cibil)
        return self


class Property(BaseModel):
    """The property being financed."""

    model_config = ConfigDict(frozen=True)

    value: Decimal = Field(gt=0)
    type: PropertyType
    city_tier: CityTier


class LoanRequest(BaseModel):
    """What the borrower is asking for.

    ``requested_amount`` is optional for a new loan (the engine reports the max it
    can offer). ``existing_loan_outstanding`` and ``existing_rate_pct`` are used by
    balance-transfer and top-up products.
    """

    model_config = ConfigDict(frozen=True)

    product_type: ProductType
    requested_amount: Decimal | None = Field(default=None, gt=0)
    requested_tenure_years: int = Field(gt=0, le=40)
    existing_loan_outstanding: Decimal = Field(default=Decimal(0), ge=0)
    existing_rate_pct: Decimal | None = Field(default=None, ge=0)


class BorrowerProfile(BaseModel):
    """A complete borrower profile: the single input to the engine."""

    model_config = ConfigDict(frozen=True)

    applicant: Applicant
    co_applicants: tuple[CoApplicant, ...] = ()
    existing_monthly_obligations: Decimal = Field(default=Decimal(0), ge=0)
    property: Property
    loan_request: LoanRequest

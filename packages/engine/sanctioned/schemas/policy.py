"""A lender's declarative, versioned eligibility policy.

This is the heart of the "policy-as-code" design: engine logic is generic, and
lenders differ *only* in this data. These models perform structural and
field-level validation (types, non-negativity, ranges). Richer cross-field
business invariants — FOIR caps, monotonic LTV bands, gap-free CIBIL coverage —
are asserted by :mod:`sanctioned.validation.policy_validator` so that failures can
be reported against a specific ``lender_id`` and field.

Policies are immutable once loaded; ``policy_diff`` compares two frozen snapshots.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from sanctioned.schemas.enums import (
    CityTier,  # noqa: F401  (kept for readers; metro logic lives on the enum)
    Decision,
    EmployerCategory,
    LenderType,
    ProductType,
    PropertyType,
)

_FROZEN = ConfigDict(frozen=True)


class AgeBlock(BaseModel):
    """Entry and maturity age limits for one employment class."""

    model_config = _FROZEN

    min_entry: int = Field(ge=18, le=100)
    max_at_maturity: int = Field(ge=18, le=100)


class AgeRules(BaseModel):
    """Age limits split by employment class."""

    model_config = _FROZEN

    salaried: AgeBlock
    self_employed: AgeBlock


class TenureRule(BaseModel):
    """Maximum loan tenure the lender offers, in years."""

    model_config = _FROZEN

    max_years: int = Field(gt=0, le=40)


class FoirBand(BaseModel):
    """A FOIR cap that applies up to a net-monthly-income ceiling.

    ``up_to_nmi = None`` is the catch-all top band (no upper income limit).
    Bands are ordered; the first band whose ceiling is ≥ the assessed income wins.
    """

    model_config = _FROZEN

    up_to_nmi: Decimal | None = Field(default=None, gt=0)
    cap_pct: Decimal = Field(gt=0)


class FoirRules(BaseModel):
    """FOIR bands split by employment class."""

    model_config = _FROZEN

    salaried: tuple[FoirBand, ...]
    self_employed: tuple[FoirBand, ...]


class NmiMultiplier(BaseModel):
    """Loan as a multiple of net monthly income (the multiplier bound)."""

    model_config = _FROZEN

    min: Decimal = Field(gt=0)
    max: Decimal = Field(gt=0)


class LtvBand(BaseModel):
    """A maximum LTV that applies up to a loan-amount ceiling.

    ``up_to_amount = None`` is the catch-all top band. Bands are keyed off the
    loan amount; the engine solves for the self-consistent band.
    """

    model_config = _FROZEN

    up_to_amount: Decimal | None = Field(default=None, gt=0)
    max_ltv_pct: Decimal = Field(gt=0, le=90)


class MinIncomeRule(BaseModel):
    """Minimum net monthly income, split metro vs non-metro."""

    model_config = _FROZEN

    metro: Decimal = Field(ge=0)
    non_metro: Decimal = Field(ge=0)


class MinIncomeRules(BaseModel):
    """Minimum-income floors split by employment class."""

    model_config = _FROZEN

    salaried: MinIncomeRule
    self_employed: MinIncomeRule


class CibilTier(BaseModel):
    """A CIBIL band mapping a score range to a decision and indicative rate.

    The thin/no-file case is encoded as ``min_score == max_score == -1``.
    ``rate_pct`` must be present unless the band's decision is REJECT.
    """

    model_config = _FROZEN

    min_score: int
    max_score: int
    decision: Decision
    rate_pct: Decimal | None = Field(default=None, gt=0)


class SelfEmployedRule(BaseModel):
    """Gates specific to self-employed applicants."""

    model_config = _FROZEN

    min_business_vintage_years: Decimal = Field(ge=0)
    itr_years_required: int = Field(ge=0)


class PropertyRule(BaseModel):
    """Per-property-type acceptance and optional bound overrides.

    Property types absent from a policy's list default to allowed with no
    override.
    """

    model_config = _FROZEN

    type: PropertyType
    allowed: bool = True
    ltv_override_pct: Decimal | None = Field(default=None, gt=0, le=90)
    tenure_override_years: int | None = Field(default=None, gt=0, le=40)


class EmployerPerk(BaseModel):
    """FOIR bonus and rate discount granted to an employer category."""

    model_config = _FROZEN

    category: EmployerCategory
    foir_bonus_pct: Decimal = Field(default=Decimal(0), ge=0)
    rate_discount_bps: int = Field(default=0, ge=0)


class CoApplicantRule(BaseModel):
    """Whether and how co-applicant income may be combined."""

    model_config = _FROZEN

    allowed: bool = True
    combine_income: bool = True
    max_count: int = Field(default=2, ge=0)


class ProductOverride(BaseModel):
    """Per-product tweaks applied on top of the base policy.

    Only the fields relevant to a given product are set; the rest stay ``None``.
    """

    model_config = _FROZEN

    max_ltv_pct: Decimal | None = Field(default=None, gt=0, le=90)
    min_seasoning_months: int | None = Field(default=None, ge=0)
    combined_max_ltv_pct: Decimal | None = Field(default=None, gt=0, le=90)


class LenderLimits(BaseModel):
    """Absolute loan-amount floor and ceiling for the lender."""

    model_config = _FROZEN

    min_loan: Decimal = Field(gt=0)
    max_loan: Decimal = Field(gt=0)


class LenderPolicy(BaseModel):
    """A single lender's complete, versioned eligibility policy."""

    model_config = _FROZEN

    lender_id: str = Field(min_length=1)
    lender_name: str = Field(min_length=1)
    lender_type: LenderType
    policy_version: str = Field(min_length=1)
    effective_date: date
    source: str = Field(min_length=1)
    disclaimer: str = Field(min_length=1)
    products: tuple[ProductType, ...]

    age: AgeRules
    tenure: TenureRule
    foir: FoirRules
    nmi_multiplier: NmiMultiplier
    ltv_bands: tuple[LtvBand, ...]
    min_income: MinIncomeRules
    cibil_tiers: tuple[CibilTier, ...]
    self_employed: SelfEmployedRule
    property_rules: tuple[PropertyRule, ...] = ()
    variable_pay_haircut_pct: Decimal = Field(default=Decimal(50), ge=0, le=100)
    employer_category_perks: tuple[EmployerPerk, ...] = ()
    co_applicant: CoApplicantRule = CoApplicantRule()
    product_overrides: dict[ProductType, ProductOverride] = Field(default_factory=dict)
    limits: LenderLimits

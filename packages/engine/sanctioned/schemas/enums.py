"""Closed sets of domain values.

Every field whose universe of values is known and finite uses one of these enums
rather than a bare ``str``. This keeps policy YAML, borrower inputs, and results
self-validating: an unknown value fails fast at parse time instead of silently
flowing through the rules.

All enums subclass ``str`` so they serialise to readable values in JSON and YAML.
"""

from __future__ import annotations

from enum import StrEnum


class EmploymentType(StrEnum):
    """How the applicant earns income — drives which policy blocks apply."""

    SALARIED = "SALARIED"
    SELF_EMPLOYED_PROFESSIONAL = "SELF_EMPLOYED_PROFESSIONAL"
    SELF_EMPLOYED_BUSINESS = "SELF_EMPLOYED_BUSINESS"

    @property
    def is_self_employed(self) -> bool:
        """True for both self-employed variants (professional and business)."""
        return self is not EmploymentType.SALARIED


class ProductType(StrEnum):
    """The loan product being matched."""

    NEW_HOME_LOAN = "NEW_HOME_LOAN"
    BALANCE_TRANSFER = "BALANCE_TRANSFER"
    TOP_UP = "TOP_UP"


class LenderType(StrEnum):
    """The kind of institution issuing the policy."""

    PUBLIC_BANK = "PUBLIC_BANK"
    PRIVATE_BANK = "PRIVATE_BANK"
    HFC = "HFC"  # Housing Finance Company
    NBFC = "NBFC"  # Non-Banking Financial Company


class PropertyType(StrEnum):
    """The nature of the property being financed."""

    APPROVED_RESALE = "APPROVED_RESALE"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    NEW_FROM_BUILDER = "NEW_FROM_BUILDER"
    PLOT_PLUS_CONSTRUCTION = "PLOT_PLUS_CONSTRUCTION"
    SELF_CONSTRUCTION = "SELF_CONSTRUCTION"


class CityTier(StrEnum):
    """Location tier — gates the metro vs non-metro minimum-income test."""

    METRO = "METRO"
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"

    @property
    def is_metro(self) -> bool:
        """METRO and TIER_1 are treated as 'metro' for minimum-income checks."""
        return self in (CityTier.METRO, CityTier.TIER_1)


class Decision(StrEnum):
    """The outcome of an eligibility evaluation."""

    APPROVE = "APPROVE"
    REFER = "REFER"
    REJECT = "REJECT"


class Constraint(StrEnum):
    """Which bound produced the final (minimum) sanction amount."""

    FOIR = "FOIR"
    LTV = "LTV"
    NMI_MULTIPLIER = "NMI_MULTIPLIER"
    LENDER_MAX_CAP = "LENDER_MAX_CAP"
    TENURE = "TENURE"


class EmployerCategory(StrEnum):
    """Employer grading used for FOIR bonuses and rate discounts.

    ``SUPER_CAT`` covers premier employers (PSUs, listed MNCs, etc.).
    """

    SUPER_CAT = "SUPER_CAT"
    CAT_A = "CAT_A"
    CAT_B = "CAT_B"
    CAT_C = "CAT_C"
    UNCATEGORIZED = "UNCATEGORIZED"

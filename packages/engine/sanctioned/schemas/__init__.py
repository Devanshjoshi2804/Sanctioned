"""Typed domain models — the contract every other layer depends on.

The schemas are split by concern:

* :mod:`sanctioned.schemas.enums` — closed sets of domain values.
* :mod:`sanctioned.schemas.borrower` — the borrower-side inputs.
* :mod:`sanctioned.schemas.policy` — a lender's declarative, versioned policy.
* :mod:`sanctioned.schemas.result` — the engine's explainable output.

Re-exported here so callers can ``from sanctioned.schemas import BorrowerProfile``.
"""

from sanctioned.schemas.borrower import (
    Applicant,
    BorrowerProfile,
    CoApplicant,
    LoanRequest,
    Property,
)
from sanctioned.schemas.enums import (
    CityTier,
    Constraint,
    Decision,
    EmployerCategory,
    EmploymentType,
    LenderType,
    ProductType,
    PropertyType,
)
from sanctioned.schemas.policy import (
    AgeBlock,
    AgeRules,
    CibilTier,
    CoApplicantRule,
    EmployerPerk,
    FoirBand,
    FoirRules,
    LenderLimits,
    LenderPolicy,
    LtvBand,
    MinIncomeRule,
    MinIncomeRules,
    NmiMultiplier,
    ProductOverride,
    PropertyRule,
    SelfEmployedRule,
    TenureRule,
)
from sanctioned.schemas.result import (
    Bounds,
    EligibilityResult,
    MatchResult,
    MatchSummary,
    ReasonTrace,
)

__all__ = [
    # policy
    "AgeBlock",
    "AgeRules",
    # borrower
    "Applicant",
    "BorrowerProfile",
    # result
    "Bounds",
    "CibilTier",
    # enums
    "CityTier",
    "CoApplicant",
    "CoApplicantRule",
    "Constraint",
    "Decision",
    "EligibilityResult",
    "EmployerCategory",
    "EmployerPerk",
    "EmploymentType",
    "FoirBand",
    "FoirRules",
    "LenderLimits",
    "LenderPolicy",
    "LenderType",
    "LoanRequest",
    "LtvBand",
    "MatchResult",
    "MatchSummary",
    "MinIncomeRule",
    "MinIncomeRules",
    "NmiMultiplier",
    "ProductOverride",
    "ProductType",
    "Property",
    "PropertyRule",
    "PropertyType",
    "ReasonTrace",
    "SelfEmployedRule",
    "TenureRule",
]

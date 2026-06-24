"""Property-type acceptance and bound overrides (spec §5.4, §5.5).

A policy may list per-property-type rules. A type that is present and disallowed
is a hard rejection (``PROPERTY_TYPE``). A type absent from the list defaults to
allowed with no overrides. Allowed types may carry tighter LTV or tenure caps.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import ReasonTrace


@dataclass(frozen=True)
class PropertyOutcome:
    """Result of the property-type rule."""

    allowed: bool
    ltv_override_pct: Decimal | None
    tenure_override_years: int | None
    trace: ReasonTrace


def evaluate_property(profile: BorrowerProfile, policy: LenderPolicy) -> PropertyOutcome:
    """Resolve acceptance and any LTV/tenure overrides for the property type."""
    property_type = profile.property.type
    rule = next((r for r in policy.property_rules if r.type is property_type), None)

    if rule is None:
        allowed, ltv_override, tenure_override = True, None, None
    else:
        allowed = rule.allowed
        ltv_override = rule.ltv_override_pct
        tenure_override = rule.tenure_override_years

    if allowed:
        override_bits = []
        if ltv_override is not None:
            override_bits.append(f"LTV<={ltv_override}%")
        if tenure_override is not None:
            override_bits.append(f"tenure<={tenure_override}y")
        suffix = f" ({', '.join(override_bits)})" if override_bits else ""
        detail = f"Property type {property_type.value} is accepted{suffix}"
    else:
        detail = f"Property type {property_type.value} is not funded by this lender"

    trace = ReasonTrace(
        code="PROPERTY_TYPE",
        rule="Property type acceptance",
        passed=allowed,
        value=property_type.value,
        threshold="allowed" if allowed else "not allowed",
        detail=detail,
    )
    return PropertyOutcome(
        allowed=allowed,
        ltv_override_pct=ltv_override,
        tenure_override_years=tenure_override,
        trace=trace,
    )

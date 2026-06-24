"""Small shared helpers for the rule layer.

Kept private (leading underscore) — these are formatting and selection utilities
for building reason traces, not part of the engine's public surface.
"""

from __future__ import annotations

from decimal import Decimal

from sanctioned.emi import round_rupees

HUNDRED = Decimal(100)


def rupees(amount: Decimal) -> str:
    """Format a money amount as whole rupees with thousands separators."""
    return f"₹{round_rupees(amount):,}"


def percent(value: Decimal) -> str:
    """Format a percentage value, trimming trailing zeros (e.g. ``8.10`` -> ``8.1%``)."""
    normalized = value.normalize()
    # Avoid scientific notation for whole numbers like 60 -> "6E+1".
    text = format(normalized, "f")
    return f"{text}%"

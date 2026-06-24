"""Deterministic lender-policy eligibility & matching engine.

This package is the single source of truth for business rules. It exposes pure,
typed functions over Pydantic models; no web, UI, or persistence concerns live
here. See ``CLAUDE.md`` for the full specification.
"""

__version__ = "0.1.0"

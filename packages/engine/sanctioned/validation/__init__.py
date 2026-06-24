"""Validation layer: policy invariants and (later) data-feed checks.

Kept separate from the Pydantic schemas so that cross-field business rules can be
reported against a specific lender and field, and so the data-validation surface
(a JD requirement) is an explicit, testable module.
"""

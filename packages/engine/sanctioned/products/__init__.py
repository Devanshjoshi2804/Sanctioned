"""Product flows — per-lender evaluation for each loan product.

Each product module composes the rule layer into a single
:class:`~sanctioned.schemas.result.EligibilityResult` for one borrower against one
policy. Phase 1 implements ``new_loan`` (NEW_HOME_LOAN); balance transfer and
top-up arrive in Phase 3.
"""

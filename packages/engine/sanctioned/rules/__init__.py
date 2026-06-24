"""The rule layer — the only home of lending business logic.

Each module is a small, pure unit that takes a borrower and a policy (plus any
already-computed context) and returns a typed datum together with the
:class:`~sanctioned.schemas.result.ReasonTrace`(s) it produced. Rules never mutate
their inputs and never perform I/O. The orchestrator in
:mod:`sanctioned.engine` composes them; the explainability comes from the traces
they emit, one per evaluated rule, in evaluation order.
"""

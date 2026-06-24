"""Retrieval-augmented ops copilot over the policy registry and runbook.

The copilot answers operational questions strictly from retrieved sources, each
answer carrying citations back to the policy file or runbook section it came from.
It never answers from the language model's own knowledge — when the corpus has no
support, it says so.
"""

from sanctioned_copilot.copilot import Answer, Citation, Copilot

__all__ = ["Answer", "Citation", "Copilot"]
__version__ = "0.1.0"

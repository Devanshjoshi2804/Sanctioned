"""FastAPI service exposing the sanctioned matching engine.

A thin transport layer: it validates requests, delegates to the engine library,
and serialises responses. No business rule lives here.
"""

__version__ = "0.1.0"

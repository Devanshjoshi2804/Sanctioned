"""FastAPI application wiring the engine to HTTP.

Endpoints (spec §9.1):

* ``POST /match``            — a borrower profile -> a ranked match result
* ``GET  /lenders``         — all lender policies (with provenance)
* ``GET  /lenders/{id}``    — one lender policy
* ``POST /policy-diff``     — impact report between a head policy set and a base
* ``POST /validate``        — run feed validation over personas/offers

The engine is imported as a library; this module contains no business rules.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sanctioned.engine import match
from sanctioned.policy_diff import diff_registries
from sanctioned.registry import Registry, load_bundled_registry
from sanctioned.samples import generate_personas
from sanctioned.schemas.borrower import BorrowerProfile
from sanctioned.schemas.policy import LenderPolicy
from sanctioned.schemas.result import MatchResult
from sanctioned.validation.feed_validator import (
    offer_records,
    persona_records,
    render_report,
    validate_offer_feed,
    validate_persona_feed,
)
from sanctioned.validation.policy_validator import PolicyValidationError, validate_policy
from sanctioned_api.serializers import serialize_diff_report, serialize_feed_report

app = FastAPI(
    title="sanctioned API",
    version="0.1.0",
    summary="Deterministic lender-policy eligibility & matching engine.",
)

# The dashboard is served from a different origin in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_REGISTRY = load_bundled_registry()


def _registry_from_dicts(policies: list[dict[str, Any]]) -> Registry:
    """Build and validate a registry from raw policy dictionaries."""
    parsed: dict[str, LenderPolicy] = {}
    for raw in policies:
        try:
            policy = LenderPolicy.model_validate(raw)
            validate_policy(policy)
        except PolicyValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=f"invalid policy: {error}") from error
        parsed[policy.lender_id] = policy
    return Registry(parsed)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "lenders": str(len(_REGISTRY))}


@app.post("/match", response_model=MatchResult)
def post_match(profile: BorrowerProfile) -> MatchResult:
    """Match a borrower against the full lender panel."""
    return match(profile, _REGISTRY)


@app.get("/lenders", response_model=list[LenderPolicy])
def get_lenders() -> list[LenderPolicy]:
    """Return every lender policy, with provenance."""
    return list(_REGISTRY)


@app.get("/lenders/{lender_id}", response_model=LenderPolicy)
def get_lender(lender_id: str) -> LenderPolicy:
    """Return a single lender policy by id."""
    try:
        return _REGISTRY.get(lender_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown lender '{lender_id}'") from error


class PolicyDiffRequest(BaseModel):
    """Head policy set to compare; base defaults to the bundled registry."""

    head_policies: list[dict[str, Any]] = Field(min_length=1)
    base_policies: list[dict[str, Any]] | None = None


@app.post("/policy-diff")
def post_policy_diff(body: PolicyDiffRequest) -> dict[str, Any]:
    """Compute the matching-impact report between two policy sets."""
    base = _registry_from_dicts(body.base_policies) if body.base_policies else _REGISTRY
    head = _registry_from_dicts(body.head_policies)
    report = diff_registries(base, head, generate_personas())
    return serialize_diff_report(report)


class ValidateRequest(BaseModel):
    """Optional persona/offer feeds; each defaults to the bundled data."""

    personas: list[dict[str, Any]] | None = None
    offers: list[dict[str, Any]] | None = None


@app.post("/validate")
def post_validate(body: ValidateRequest) -> dict[str, Any]:
    """Validate persona and lender-offer feeds, returning structured + Markdown output."""
    persona_feed = (
        body.personas if body.personas is not None else persona_records(generate_personas())
    )
    offer_feed = body.offers if body.offers is not None else offer_records(_REGISTRY)
    reports = [validate_persona_feed(persona_feed), validate_offer_feed(offer_feed)]
    return {
        "reports": [serialize_feed_report(r) for r in reports],
        "markdown": render_report(reports),
        "ok": all(r.ok for r in reports),
    }

"""Tests for the FastAPI service, driven through Starlette's TestClient."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from sanctioned_api.main import app

client = TestClient(app)


def _prime_borrower(product: str = "NEW_HOME_LOAN", **loan: Any) -> dict[str, Any]:
    return {
        "applicant": {
            "age": 34,
            "employment_type": "SALARIED",
            "net_monthly_income": "90000",
            "cibil": 805,
        },
        "existing_monthly_obligations": "12000",
        "property": {"value": "7000000", "type": "APPROVED_RESALE", "city_tier": "METRO"},
        "loan_request": {
            "product_type": product,
            "requested_tenure_years": 20,
            **loan,
        },
    }


class TestMatch:
    def test_match_returns_ranked_results(self) -> None:
        response = client.post("/match", json=_prime_borrower())
        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) == 4
        assert body["summary"]["eligible_count"] >= 1
        # Results are eligible-first.
        flags = [r["eligible"] for r in body["results"]]
        assert flags == sorted(flags, reverse=True)

    def test_match_includes_reason_traces(self) -> None:
        body = client.post("/match", json=_prime_borrower()).json()
        for result in body["results"]:
            assert len(result["reasons"]) >= 1

    def test_invalid_borrower_is_rejected_422(self) -> None:
        bad = _prime_borrower()
        bad["applicant"]["cibil"] = 2000  # out of range
        assert client.post("/match", json=bad).status_code == 422


class TestLenders:
    def test_list_lenders(self) -> None:
        response = client.get("/lenders")
        assert response.status_code == 200
        ids = {p["lender_id"] for p in response.json()}
        assert {"psu_bank", "private_bank", "hfc", "nbfc"} <= ids

    def test_get_one_lender_has_provenance(self) -> None:
        body = client.get("/lenders/psu_bank").json()
        assert body["lender_id"] == "psu_bank"
        assert body["disclaimer"]
        assert body["source"]

    def test_unknown_lender_404(self) -> None:
        assert client.get("/lenders/nope").status_code == 404


class TestPolicyDiff:
    def test_diff_against_modified_head(self) -> None:
        lenders = client.get("/lenders").json()
        # Tighten every PSU FOIR cap in the head set.
        for policy in lenders:
            if policy["lender_id"] == "psu_bank":
                for band in policy["foir"]["salaried"]:
                    band["cap_pct"] = "40"
                for band in policy["foir"]["self_employed"]:
                    band["cap_pct"] = "40"
        response = client.post("/policy-diff", json={"head_policies": lenders})
        assert response.status_code == 200
        body = response.json()
        assert body["has_changes"] is True
        psu = next(d for d in body["lender_diffs"] if d["lender_id"] == "psu_bank")
        assert psu["status"] == "changed"

    def test_invalid_head_policy_422(self) -> None:
        response = client.post("/policy-diff", json={"head_policies": [{"lender_id": "x"}]})
        assert response.status_code == 422


class TestValidate:
    def test_default_feeds_pass(self) -> None:
        body = client.post("/validate", json={}).json()
        assert body["ok"] is True
        assert any(r["feed"] == "persona_feed" for r in body["reports"])

    def test_bad_persona_feed_flagged(self) -> None:
        payload = {
            "personas": [
                {
                    "net_monthly_income": -1.0,
                    "cibil": 5000,
                    "property_value": 0.0,
                    "existing_obligations": 0.0,
                    "age": 30,
                }
            ]
        }
        body = client.post("/validate", json=payload).json()
        assert body["ok"] is False


class TestIngestSandbox:
    def test_derives_autofill_from_mock_statement(self) -> None:
        body = client.post("/ingest/sandbox", json={}).json()
        assert body["autofill"]["net_monthly_income"] == "90000"
        assert body["autofill"]["existing_monthly_obligations"] == "12000"
        assert body["derived"]["salary_regularity"] == "REGULAR"
        assert "sandbox" in body["derived"]["disclaimer"].lower()

    def test_irregular_salary_is_flagged(self) -> None:
        body = client.post("/ingest/sandbox", json={"months": 4, "skip_salary_month": 1}).json()
        assert body["derived"]["salary_regularity"] == "IRREGULAR"


class TestAsk:
    def test_answers_with_citations(self) -> None:
        body = client.post(
            "/ask",
            json={"question": "Which lenders accept self-employed with two years of ITR?"},
        ).json()
        assert body["answer"]
        assert len(body["citations"]) >= 1
        assert body["backend"] in {"offline", "gemini"}

    def test_empty_question_is_rejected(self) -> None:
        assert client.post("/ask", json={"question": ""}).status_code == 422


@pytest.mark.parametrize("path", ["/health", "/openapi.json"])
def test_service_endpoints(path: str) -> None:
    assert client.get(path).status_code == 200

"""Tests for sandbox AA ingestion: statement -> derived financials -> autofill."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sanctioned_ingest.autofill import profile_autofill
from sanctioned_ingest.derive import derive_financials
from sanctioned_ingest.setu import (
    SetuAaClient,
    SetuConfig,
    SetuCredentialsError,
    map_fi_data_to_statement,
)
from sanctioned_ingest.source import MockStatementSource, SetuAaSource
from sanctioned_ingest.statement import TxnCategory

# A representative Setu AA session payload (the shape the FIP returns).
_SESSION_PAYLOAD: dict[str, Any] = {
    "status": "COMPLETED",
    "fips": [
        {
            "fipID": "SETU-FIP",
            "accounts": [
                {
                    "maskedAccNumber": "XXXXXX1234",
                    "data": {
                        "account": {
                            "transactions": {
                                "transaction": [
                                    {
                                        "type": "CREDIT",
                                        "amount": "90000.00",
                                        "narration": "NEFT SALARY ACME CORP",
                                        "transactionTimestamp": "2026-02-01T10:00:00+05:30",
                                    },
                                    {
                                        "type": "DEBIT",
                                        "amount": "12000.00",
                                        "narration": "ACH EMI AUTO LOAN",
                                        "transactionTimestamp": "2026-02-05T09:00:00+05:30",
                                    },
                                    {
                                        "type": "DEBIT",
                                        "amount": "8500.00",
                                        "narration": "UPI GROCERIES",
                                        "transactionTimestamp": "2026-02-18T20:00:00+05:30",
                                    },
                                ]
                            }
                        }
                    },
                }
            ],
        }
    ],
}


class TestMockStatement:
    def test_has_salary_and_emi_each_month(self) -> None:
        statement = MockStatementSource(months=4).fetch()
        assert len(statement.months()) == 4
        salary = [t for t in statement.transactions if t.category.value == "SALARY"]
        emi = [t for t in statement.transactions if t.category.value == "EMI"]
        assert len(salary) == 4
        assert len(emi) == 4

    def test_is_deterministic(self) -> None:
        assert MockStatementSource().fetch() == MockStatementSource().fetch()


class TestDerive:
    def test_derives_income_and_obligations(self) -> None:
        statement = MockStatementSource(
            monthly_salary=Decimal("90000"), monthly_emi=Decimal("12000"), months=4
        ).fetch()
        derived = derive_financials(statement)
        assert derived.net_monthly_income == Decimal("90000")
        assert derived.existing_monthly_obligations == Decimal("12000")
        assert derived.salary_regularity == "REGULAR"
        assert derived.regularity_score == Decimal("1.00")
        assert derived.months_observed == 4
        assert "sandbox" in derived.disclaimer.lower()

    def test_missing_salary_month_lowers_regularity(self) -> None:
        statement = MockStatementSource(months=4, skip_salary_month=2).fetch()
        derived = derive_financials(statement)
        assert derived.regularity_score == Decimal("0.75")
        assert derived.salary_regularity == "IRREGULAR"
        # Income still derives from the months that do have salary.
        assert derived.net_monthly_income == Decimal("90000")

    def test_single_month_is_insufficient(self) -> None:
        statement = MockStatementSource(months=1).fetch()
        derived = derive_financials(statement)
        assert derived.salary_regularity == "INSUFFICIENT"


class TestAutofill:
    def test_maps_to_form_fields(self) -> None:
        derived = derive_financials(MockStatementSource().fetch())
        fields = profile_autofill(derived)
        assert fields["net_monthly_income"] == "90000"
        assert fields["existing_monthly_obligations"] == "12000"


class TestSetuMapping:
    def test_maps_fi_data_to_categorised_transactions(self) -> None:
        statement = map_fi_data_to_statement(_SESSION_PAYLOAD)
        assert len(statement.transactions) == 3
        by_category = {t.category for t in statement.transactions}
        assert TxnCategory.SALARY in by_category
        assert TxnCategory.EMI in by_category
        # The mapped statement derives the same figures as the mock would.
        derived = derive_financials(statement)
        assert derived.net_monthly_income == Decimal("90000")
        assert derived.existing_monthly_obligations == Decimal("12000")

    def test_credit_is_positive_debit_is_negative(self) -> None:
        statement = map_fi_data_to_statement(_SESSION_PAYLOAD)
        salary = next(t for t in statement.transactions if t.category is TxnCategory.SALARY)
        emi = next(t for t in statement.transactions if t.category is TxnCategory.EMI)
        assert salary.amount > 0
        assert emi.amount < 0


class TestSetuClient:
    def test_fetch_statement_drives_the_real_session_flow(self) -> None:
        seen_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen_headers.update(request.headers)
            if request.method == "POST" and request.url.path == "/sessions":
                return httpx.Response(200, json={"id": "sess-1", "status": "PENDING"})
            if request.method == "GET" and request.url.path == "/sessions/sess-1":
                return httpx.Response(200, json=_SESSION_PAYLOAD)
            return httpx.Response(404, json={"error": request.url.path})

        config = SetuConfig(client_id="cid", client_secret="sec", product_instance_id="pid")
        http = httpx.Client(transport=httpx.MockTransport(handler), base_url=config.base_url)
        client = SetuAaClient(config, client=http)

        statement = client.fetch_statement(
            "consent-1", from_date=date(2026, 1, 1), to_date=date(2026, 3, 1)
        )
        assert len(statement.transactions) == 3
        # The Setu auth headers were sent on the request.
        assert seen_headers["x-client-id"] == "cid"
        assert seen_headers["x-product-instance-id"] == "pid"

    def test_rejected_credentials_raise_a_clear_error(self) -> None:
        # Mirrors the real sandbox behaviour when KYC is incomplete (401).
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "INVALID_CREDENTIALS"})

        config = SetuConfig(client_id="cid", client_secret="sec", product_instance_id="pid")
        http = httpx.Client(transport=httpx.MockTransport(handler), base_url=config.base_url)
        client = SetuAaClient(config, client=http)
        with pytest.raises(SetuCredentialsError, match="KYC"):
            client.start_consent("v@aa", from_date=date(2026, 1, 1), to_date=date(2026, 3, 1))

    def test_start_consent_returns_approval_url(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "consent-req-1",
                    "url": "https://fiu-sandbox.setu.co/consents/webview/consent-req-1",
                    "status": "PENDING",
                },
            )

        config = SetuConfig(client_id="cid", client_secret="sec", product_instance_id="pid")
        http = httpx.Client(transport=httpx.MockTransport(handler), base_url=config.base_url)
        client = SetuAaClient(config, client=http)

        consent = client.start_consent(
            "9999999999@onemoney", from_date=date(2026, 1, 1), to_date=date(2026, 3, 1)
        )
        assert consent.consent_request_id == "consent-req-1"
        assert "webview" in consent.approval_url


class TestSetuConfig:
    def test_from_env_requires_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SETU_CLIENT_ID", raising=False)
        with pytest.raises(RuntimeError, match="SETU_CLIENT_ID"):
            SetuConfig.from_env()

    def test_source_construction_requires_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SETU_CLIENT_ID", raising=False)
        with pytest.raises(RuntimeError):
            SetuAaSource("consent-1")

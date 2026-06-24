"""Real Setu Account-Aggregator (AA) sandbox client.

This implements the actual AA REST flow against Setu's FIU APIs — consent →
data session → fetch → map to a :class:`BankStatement`. It performs real HTTP
calls when credentials are configured; there is no synthetic data here. The mock
generator in :mod:`sanctioned_ingest.source` remains the offline fallback.

Auth is two-step (verified live against the Setu sandbox): exchange the client
id/secret for a Bearer token at the central auth host (``/users/login`` with the
``client: bridge`` header), then call the ``/v2`` FIU endpoints with that token plus
``x-product-instance-id``.

Configuration comes from the environment (sandbox credentials from the Setu Bridge
console): ``SETU_CLIENT_ID``, ``SETU_CLIENT_SECRET``, ``SETU_PRODUCT_INSTANCE_ID``
(and optional ``SETU_AA_BASE_URL`` / ``SETU_AUTH_BASE_URL``).

The AA consent step is interactive (the customer approves in their AA app via the
returned web-view URL), so the flow is split: :meth:`SetuAaClient.start_consent`
returns the approval URL, and once the consent is ACTIVE,
:meth:`SetuAaClient.fetch_statement` pulls the data. The FI-data parser is
deliberately tolerant of the nesting variants Setu returns across FIPs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from sanctioned_ingest.statement import BankStatement, BankTransaction, TxnCategory

# The FIU data APIs are environment-specific; auth (login) is a single central host.
_DATA_BASE_URL = "https://fiu-sandbox.setu.co"
_AUTH_BASE_URL = "https://orgservice-prod.setu.co/v1"
_DEFAULT_TIMEOUT = 30.0

# Narration keywords used to categorise AA transactions.
_SALARY_HINTS = ("salary", "sal cr", "sal-", "neft sal", "payroll")
_EMI_HINTS = ("emi", "ach", "loan", "mandate", "nach")


@dataclass(frozen=True)
class SetuConfig:
    """Setu AA FIU credentials and hosts."""

    client_id: str
    client_secret: str
    product_instance_id: str
    data_base_url: str = _DATA_BASE_URL
    auth_base_url: str = _AUTH_BASE_URL

    @classmethod
    def from_env(cls) -> SetuConfig:
        """Load config from SETU_* environment variables, or raise if incomplete."""
        try:
            return cls(
                client_id=os.environ["SETU_CLIENT_ID"],
                client_secret=os.environ["SETU_CLIENT_SECRET"],
                product_instance_id=os.environ["SETU_PRODUCT_INSTANCE_ID"],
                data_base_url=os.environ.get("SETU_AA_BASE_URL", _DATA_BASE_URL),
                auth_base_url=os.environ.get("SETU_AUTH_BASE_URL", _AUTH_BASE_URL),
            )
        except KeyError as missing:
            raise RuntimeError(f"missing Setu AA env var: {missing}") from missing


@dataclass(frozen=True)
class ConsentRequest:
    """The handle and approval URL returned when a consent is created."""

    consent_request_id: str
    approval_url: str
    status: str


class SetuAaClient:
    """Client for Setu's AA FIU v2 APIs.

    Auth is two-step: exchange the client id/secret for a Bearer access token at the
    central auth host (``/users/login`` with the ``client: bridge`` header), then
    call the ``/v2`` FIU endpoints with that token plus the product-instance header.
    """

    def __init__(self, config: SetuConfig, *, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(timeout=_DEFAULT_TIMEOUT)
        self._token: str | None = None

    def _access_token(self) -> str:
        if self._token is None:
            response = self._client.post(
                f"{self._config.auth_base_url}/users/login",
                headers={"client": "bridge", "Content-Type": "application/json"},
                json={
                    "clientID": self._config.client_id,
                    "secret": self._config.client_secret,
                    "grant_type": "client_credentials",
                },
            )
            _raise_for_status(response)
            self._token = str(_as_dict(response.json())["access_token"])
        return self._token

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token()}",
            "x-product-instance-id": self._config.product_instance_id,
        }

    def start_consent(
        self,
        vua: str,
        *,
        from_date: date,
        to_date: date,
        duration_months: int = 24,
        consent_mode: str = "STORE",
        data_life_months: int = 3,
    ) -> ConsentRequest:
        """Create a consent request; the customer approves it at ``approval_url``."""
        payload: dict[str, Any] = {
            "consentDuration": {"unit": "MONTH", "value": str(duration_months)},
            "vua": vua,
            "dataRange": {"from": _iso(from_date), "to": _iso(to_date)},
            "context": [],
            "consentMode": consent_mode,
            "dataLife": {"unit": "MONTH", "value": data_life_months},
        }
        body = self._post("/v2/consents", payload)
        return ConsentRequest(
            consent_request_id=str(body.get("id", "")),
            approval_url=str(body.get("url", "")),
            status=str(body.get("status", "PENDING")),
        )

    def consent_status(self, consent_request_id: str) -> dict[str, Any]:
        """Return the consent object (``status`` is PENDING/ACTIVE/REJECTED)."""
        return self._get(f"/v2/consents/{consent_request_id}")

    def create_session(self, consent_id: str, *, from_date: date, to_date: date) -> str:
        """Open a data session for an active consent; returns the session id."""
        payload = {
            "consentId": consent_id,
            "dataRange": {"from": _iso(from_date), "to": _iso(to_date)},
            "format": "json",
        }
        body = self._post("/v2/sessions", payload)
        return str(body["id"])

    def session_data(self, session_id: str) -> dict[str, Any]:
        """Fetch the FI data for a session (``status`` COMPLETED when ready)."""
        return self._get(f"/v2/sessions/{session_id}")

    def fetch_statement(
        self, consent_id: str, *, from_date: date, to_date: date, account_ref: str = "SETU-AA"
    ) -> BankStatement:
        """Open a session for an approved consent and map the result to a statement."""
        session_id = self.create_session(consent_id, from_date=from_date, to_date=to_date)
        data = self.session_data(session_id)
        return map_fi_data_to_statement(data, account_ref=account_ref)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(
            f"{self._config.data_base_url}{path}", json=payload, headers=self._headers()
        )
        _raise_for_status(response)
        return _as_dict(response.json())

    def _get(self, path: str) -> dict[str, Any]:
        response = self._client.get(f"{self._config.data_base_url}{path}", headers=self._headers())
        _raise_for_status(response)
        return _as_dict(response.json())


class SetuCredentialsError(RuntimeError):
    """Raised when Setu rejects authentication (bad client id/secret or product id)."""


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code in (401, 403):
        raise SetuCredentialsError(
            f"Setu rejected authentication ({response.status_code}: {response.text}). "
            "Check SETU_CLIENT_ID / SETU_CLIENT_SECRET and the product instance id."
        )
    response.raise_for_status()


# --- FI data mapping ----------------------------------------------------------


def map_fi_data_to_statement(
    data: dict[str, Any], *, account_ref: str = "SETU-AA"
) -> BankStatement:
    """Map a Setu AA session payload into a :class:`BankStatement`.

    Tolerant of the common nesting variants Setu returns across FIPs.
    """
    transactions: list[BankTransaction] = []
    for fip in _as_list(data.get("fips")):
        for account in _as_list(_as_dict(fip).get("accounts")):
            for raw in _iter_raw_transactions(_as_dict(account)):
                parsed = _parse_transaction(raw)
                if parsed is not None:
                    transactions.append(parsed)
    transactions.sort(key=lambda t: t.txn_date)
    return BankStatement(account_ref=account_ref, transactions=tuple(transactions))


def _iter_raw_transactions(account: dict[str, Any]) -> list[dict[str, Any]]:
    # Walk down to the transaction list, accepting the shapes Setu uses:
    # account.data[].transactions.{transaction|Transaction} or account.data.account...
    node: Any = account.get("data", account)
    candidates = node if isinstance(node, list) else [node]
    found: list[dict[str, Any]] = []
    for candidate in candidates:
        block = _as_dict(candidate)
        inner = _as_dict(block.get("account", block))
        txn_block = _as_dict(inner.get("transactions"))
        raw = txn_block.get("transaction") or txn_block.get("Transaction") or []
        found.extend(_as_dict(item) for item in _as_list(raw))
    return found


def _parse_transaction(raw: dict[str, Any]) -> BankTransaction | None:
    amount = _to_decimal(raw.get("amount"))
    if amount is None:
        return None
    txn_type = str(raw.get("type", "")).upper()
    narration = str(raw.get("narration") or raw.get("description") or "")
    timestamp = raw.get("transactionTimestamp") or raw.get("valueDate") or raw.get("txnDate")
    txn_date = _to_date(timestamp)
    if txn_date is None:
        return None
    signed = amount if txn_type == "CREDIT" else -amount
    return BankTransaction(
        txn_date=txn_date,
        amount=signed,
        description=narration or txn_type,
        category=_categorize(txn_type, narration),
    )


def _categorize(txn_type: str, narration: str) -> TxnCategory:
    text = narration.lower()
    if txn_type == "CREDIT":
        if any(hint in text for hint in _SALARY_HINTS):
            return TxnCategory.SALARY
        return TxnCategory.OTHER_CREDIT
    if any(hint in text for hint in _EMI_HINTS):
        return TxnCategory.EMI
    return TxnCategory.OTHER_DEBIT


# --- small helpers ------------------------------------------------------------


def _iso(value: date) -> str:
    # Setu expects full ISO-8601 timestamps for date ranges.
    return f"{value.isoformat()}T00:00:00Z"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return abs(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None

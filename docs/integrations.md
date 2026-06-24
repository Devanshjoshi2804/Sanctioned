# External integrations

What's real, what's sandbox-by-design, and how to go live.

## What is real (no mock)

The engine, API, dashboard, policy-diff, and copilot are real computation
end-to-end. The copilot uses **Gemini** embeddings + LLM synthesis when
`GEMINI_API_KEY` is set (offline TF-IDF retrieval otherwise) — both grounded only
in retrieved sources, with citations.

## Sandbox / indicative by design

- **Lender policies** are *indicative, public-sourced* approximations, never any
  lender's live policy (the "honest data" principle). This is intentional.
- **Account-Aggregator bank statements** default to a labelled **mock** statement.
  The integration to make this real is below.

## Account Aggregator (Setu) — bank statements

`packages/ingest/sanctioned_ingest/setu.py` implements the **real** Setu AA FIU
flow (`SetuAaClient`): it makes real HTTP calls when credentials are set. The mock
(`MockStatementSource`) stays as the offline/test fallback.

**The flow is interactive** (the customer approves consent in their AA app):

1. `client.start_consent(vua, ...)` → returns an `approval_url` (web-view). The
   customer opens it and approves.
2. Poll `client.consent_status(id)` until the consent is `ACTIVE`.
3. `client.fetch_statement(consent_id, ...)` opens a data session, fetches the FI
   data, and maps it (`map_fi_data_to_statement`) into a `BankStatement`.
4. `derive_financials(statement)` → net income, obligations, salary regularity.

**Auth is two-step** (verified live against the Setu sandbox):

1. Exchange the client id/secret for a Bearer token: `POST {auth}/users/login` with
   header `client: bridge` and body `{clientID, secret, grant_type: client_credentials}`.
2. Call the `/v2` FIU endpoints with `Authorization: Bearer <token>` and
   `x-product-instance-id`. Consent creation needs `consentMode: STORE` with a
   non-zero `dataLife` (the product default is VIEW, which requires dataLife 0).

**To go live:** put your sandbox credentials in `.env` (see `.env.example`):
`SETU_CLIENT_ID`, `SETU_CLIENT_SECRET`, `SETU_PRODUCT_INSTANCE_ID`. Then
`SetuConfig.from_env()` / `SetuAaClient` work directly — `start_consent` returns a
real approval URL (confirmed end-to-end). KYC is required only for **production
go-live**, not sandbox. After the customer approves the consent at the web-view
URL, `fetch_statement` pulls the data.

> Note: **Setu** (setu.co, Account Aggregator) is *not* the same as **API Setu**
> (apisetu.gov.in). AA is the route for bank statements. API Setu is a government
> marketplace whose **DigiLocker** (PAN/Aadhaar KYC) and **Income-Tax/ITR**
> (self-employed income) services can *supplement* the profile — but they do not
> provide the salary/EMI bank-statement feed that the AA flow does.

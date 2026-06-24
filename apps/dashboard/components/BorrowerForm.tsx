"use client";

import { useState } from "react";
import { postIngestSandbox } from "@/lib/api";

const EMPLOYMENT = ["SALARIED", "SELF_EMPLOYED_PROFESSIONAL", "SELF_EMPLOYED_BUSINESS"];
const EMPLOYER = ["UNCATEGORIZED", "SUPER_CAT", "CAT_A", "CAT_B", "CAT_C"];
const PRODUCTS = ["NEW_HOME_LOAN", "BALANCE_TRANSFER", "TOP_UP"];
const PROPERTY_TYPES = [
  "APPROVED_RESALE",
  "UNDER_CONSTRUCTION",
  "NEW_FROM_BUILDER",
  "PLOT_PLUS_CONSTRUCTION",
  "SELF_CONSTRUCTION",
];
const CITY_TIERS = ["METRO", "TIER_1", "TIER_2", "TIER_3"];

const DEFAULTS = {
  product_type: "NEW_HOME_LOAN",
  age: "34",
  employment_type: "SALARIED",
  net_monthly_income: "90000",
  variable_monthly_income: "20000",
  cibil: "805",
  employer_category: "UNCATEGORIZED",
  business_vintage_years: "5",
  itr_years_available: "3",
  existing_monthly_obligations: "12000",
  property_value: "7000000",
  property_type: "APPROVED_RESALE",
  city_tier: "METRO",
  requested_tenure_years: "20",
  existing_loan_outstanding: "4000000",
  existing_rate_pct: "9.5",
  requested_amount: "1000000",
};

type FormState = typeof DEFAULTS;

export function BorrowerForm({
  onSubmit,
  pending,
}: {
  onSubmit: (profile: unknown) => void;
  pending: boolean;
}) {
  const [state, setState] = useState<FormState>(DEFAULTS);
  const [autofillNote, setAutofillNote] = useState<string | null>(null);
  const set = (key: keyof FormState) => (value: string) =>
    setState((prev) => ({ ...prev, [key]: value }));

  const autofillFromStatement = async () => {
    setAutofillNote("Fetching sandbox statement…");
    try {
      const result = await postIngestSandbox();
      setState((prev) => ({
        ...prev,
        net_monthly_income: result.autofill.net_monthly_income,
        existing_monthly_obligations: result.autofill.existing_monthly_obligations,
      }));
      setAutofillNote(
        `Pulled from a sandbox statement over ${result.derived.months_observed} months · ` +
          `salary ${result.derived.salary_regularity.toLowerCase()}`,
      );
    } catch {
      setAutofillNote("Autofill failed — is the API running?");
    }
  };

  const isSelfEmployed = state.employment_type !== "SALARIED";
  const isBT = state.product_type === "BALANCE_TRANSFER";
  const isTopUp = state.product_type === "TOP_UP";

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    onSubmit(buildProfile(state, isSelfEmployed, isBT, isTopUp));
  };

  return (
    <form onSubmit={submit} className="space-y-5" data-testid="borrower-form">
      <Group title="Loan">
        <Select label="Product" name="product_type" value={state.product_type} onChange={set("product_type")} options={PRODUCTS} />
        <Field label="Tenure (years)" name="requested_tenure_years" value={state.requested_tenure_years} onChange={set("requested_tenure_years")} />
        {(isBT || isTopUp) && (
          <Field label="Outstanding (₹)" name="existing_loan_outstanding" value={state.existing_loan_outstanding} onChange={set("existing_loan_outstanding")} />
        )}
        {isBT && (
          <Field label="Existing rate (%)" name="existing_rate_pct" value={state.existing_rate_pct} onChange={set("existing_rate_pct")} />
        )}
        {isTopUp && (
          <Field label="Top-up sought (₹)" name="requested_amount" value={state.requested_amount} onChange={set("requested_amount")} />
        )}
      </Group>

      <Group title="Applicant">
        <Field label="Age" name="age" value={state.age} onChange={set("age")} />
        <Select label="Employment" name="employment_type" value={state.employment_type} onChange={set("employment_type")} options={EMPLOYMENT} />
        <Field label="Net income (₹/mo)" name="net_monthly_income" value={state.net_monthly_income} onChange={set("net_monthly_income")} />
        <Field label="Variable (₹/mo)" name="variable_monthly_income" value={state.variable_monthly_income} onChange={set("variable_monthly_income")} />
        <Field label="CIBIL (−1 = thin)" name="cibil" value={state.cibil} onChange={set("cibil")} />
        <Select label="Employer grade" name="employer_category" value={state.employer_category} onChange={set("employer_category")} options={EMPLOYER} />
        {isSelfEmployed && (
          <>
            <Field label="Vintage (yrs)" name="business_vintage_years" value={state.business_vintage_years} onChange={set("business_vintage_years")} />
            <Field label="ITR years" name="itr_years_available" value={state.itr_years_available} onChange={set("itr_years_available")} />
          </>
        )}
        <Field label="Other EMIs (₹/mo)" name="existing_monthly_obligations" value={state.existing_monthly_obligations} onChange={set("existing_monthly_obligations")} />
      </Group>

      <div className="rounded-sm border border-dashed border-line bg-paper/40 p-2.5">
        <button
          type="button"
          onClick={autofillFromStatement}
          data-testid="autofill-sandbox"
          className="font-display text-[12px] font-semibold text-accent hover:underline"
        >
          ↓ Autofill income from a sandbox statement
        </button>
        <p className="mt-1 text-[10px] leading-tight text-slate">
          {autofillNote ?? "Mock Account-Aggregator pull — sandbox only, no real data."}
        </p>
      </div>

      <Group title="Property">
        <Field label="Value (₹)" name="property_value" value={state.property_value} onChange={set("property_value")} />
        <Select label="Type" name="property_type" value={state.property_type} onChange={set("property_type")} options={PROPERTY_TYPES} />
        <Select label="City tier" name="city_tier" value={state.city_tier} onChange={set("city_tier")} options={CITY_TIERS} />
      </Group>

      <button
        type="submit"
        disabled={pending}
        data-testid="run-match"
        className="w-full rounded-sm bg-accent px-4 py-2.5 font-display text-sm font-semibold text-white transition-colors hover:bg-accent/90 disabled:opacity-60"
      >
        {pending ? "Matching…" : "Run match"}
      </button>
    </form>
  );
}

function buildProfile(s: FormState, isSE: boolean, isBT: boolean, isTopUp: boolean): unknown {
  return {
    applicant: {
      age: Number(s.age),
      employment_type: s.employment_type,
      net_monthly_income: s.net_monthly_income,
      variable_monthly_income: s.variable_monthly_income,
      cibil: Number(s.cibil),
      employer_category: s.employer_category,
      ...(isSE
        ? {
            business_vintage_years: s.business_vintage_years,
            itr_years_available: Number(s.itr_years_available),
          }
        : {}),
    },
    existing_monthly_obligations: s.existing_monthly_obligations,
    property: { value: s.property_value, type: s.property_type, city_tier: s.city_tier },
    loan_request: {
      product_type: s.product_type,
      requested_tenure_years: Number(s.requested_tenure_years),
      ...(isBT || isTopUp ? { existing_loan_outstanding: s.existing_loan_outstanding } : {}),
      ...(isBT ? { existing_rate_pct: s.existing_rate_pct } : {}),
      ...(isTopUp ? { requested_amount: s.requested_amount } : {}),
    },
  };
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend className="eyebrow mb-2">{title}</legend>
      <div className="grid grid-cols-2 gap-2">{children}</div>
    </fieldset>
  );
}

function Field({
  label,
  name,
  value,
  onChange,
}: {
  label: string;
  name: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="block text-[11px] text-slate">{label}</span>
      <input
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded-sm border border-line bg-surface px-2 py-1.5 font-mono text-[13px] tnum outline-none focus:border-accent focus:ring-1 focus:ring-accent"
      />
    </label>
  );
}

function Select({
  label,
  name,
  value,
  onChange,
  options,
}: {
  label: string;
  name: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="block">
      <span className="block text-[11px] text-slate">{label}</span>
      <select
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded-sm border border-line bg-surface px-2 py-1.5 text-[13px] outline-none focus:border-accent focus:ring-1 focus:ring-accent"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt.replaceAll("_", " ").toLowerCase()}
          </option>
        ))}
      </select>
    </label>
  );
}

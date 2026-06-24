import Link from "next/link";

export const metadata = {
  title: "sanctioned — lender-policy intelligence",
};

const STATS = [
  { value: "4", label: "lender archetypes" },
  { value: "3", label: "products" },
  { value: "360", label: "golden personas" },
  { value: "10", label: "property invariants" },
];

const CAPABILITIES = [
  {
    code: "DETERMINISTIC",
    title: "Deterministic engine",
    body: "Pure typed rules — no ML, no probabilistic scoring. The same borrower always gets the same verdict, so every decision is auditable.",
    href: "/match",
    cta: "Run a match",
  },
  {
    code: "REASON_TRACE",
    title: "Every verdict explained",
    body: "Each lender returns a line-by-line reason trace — the exact rule, the borrower's value, the policy threshold. The 'why didn't this customer match?' answer.",
    href: "/match",
    cta: "See a trace",
  },
  {
    code: "PRODUCTS×3",
    title: "Three loan products",
    body: "New home loan, balance transfer (with indicative savings), and top-up (combined-LTV) — one rule engine, dispatched per product.",
    href: "/match",
    cta: "Switch product",
  },
  {
    code: "POLICY_DIFF",
    title: "Regression-safe rate cards",
    body: "Change a lender's terms and replay all 360 golden personas through both versions — see who flips, how sanctions move, and which constraint starts binding.",
    href: "/policy-diff",
    cta: "Run an impact report",
  },
  {
    code: "AA_INGEST",
    title: "Consent-based autofill",
    body: "Pull a borrower's income and obligations straight from a bank statement over the Account Aggregator framework — no manual data entry.",
    href: "/match",
    cta: "Autofill a borrower",
  },
  {
    code: "HONEST_DATA",
    title: "Sourced, honest data",
    body: "Every lender number is indicative and public-sourced, traceable to its origin — never presented as a lender's live or internal policy.",
    href: "/lender/psu_bank",
    cta: "Inspect a policy",
  },
];

export default function OverviewPage() {
  return (
    <div className="space-y-10">
      <section>
        <p className="eyebrow">Lender-policy intelligence</p>
        <h1 className="mt-2 max-w-3xl font-display text-3xl font-bold leading-[1.1] tracking-tight sm:text-4xl">
          Which lenders fund this borrower, how much, at what rate — and the exact reason for every
          verdict.
        </h1>
        <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-slate">
          A deterministic, explainable matching engine across a panel of lenders, wrapped in a
          regression-safety harness and a retrieval-grounded AI copilot.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link
            href="/match"
            className="rounded-sm bg-accent px-4 py-2 font-display text-sm font-semibold text-white hover:bg-accent/90"
          >
            Run a match →
          </Link>
          <Link
            href="/ask"
            className="rounded-sm border border-line bg-surface px-4 py-2 font-display text-sm font-semibold text-ink hover:border-accent"
          >
            Ask the copilot
          </Link>
        </div>

        <dl className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-line bg-line sm:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="bg-surface px-4 py-3">
              <dt className="font-display text-2xl font-bold tnum">{s.value}</dt>
              <dd className="eyebrow mt-0.5">{s.label}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* AI highlight — the copilot gets its own band. */}
      <section className="overflow-hidden rounded-sm border border-accent/30 bg-accent/[0.04]">
        <div className="grid gap-0 md:grid-cols-[1.1fr_1fr]">
          <div className="p-6">
            <div className="flex items-center gap-2">
              <span className="rounded-sm bg-accent px-1.5 py-0.5 font-display text-[10px] font-bold uppercase tracking-wide text-white">
                AI copilot
              </span>
              <span className="eyebrow">Retrieval-augmented</span>
            </div>
            <h2 className="mt-3 font-display text-xl font-bold tracking-tight">
              Ask in plain English. Grounded only in the policies — with citations.
            </h2>
            <p className="mt-2 max-w-md text-[14px] leading-relaxed text-slate">
              The copilot retrieves from the lender policies and the ops runbook and answers with
              the sources it used. It never answers from the model&apos;s own memory, so it can&apos;t
              invent a rate or a rule.
            </p>
            <Link
              href="/ask"
              className="mt-4 inline-block font-display text-sm font-semibold text-accent hover:underline"
            >
              Open the copilot →
            </Link>
          </div>
          <div className="border-t border-accent/20 bg-surface/70 p-6 md:border-l md:border-t-0">
            <p className="text-[11px] text-slate">Example</p>
            <p className="mt-1 font-display text-[14px] font-semibold text-ink">
              “Who offers the lowest rate for a prime borrower?”
            </p>
            <p className="mt-2 text-[13px] leading-relaxed text-ink/80">
              The public-sector bank archetype offers the lowest rate, at around 8.10% for scores of
              800+.
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {["runbook · CIBIL bands", "runbook · FAQ", "psu_bank · CIBIL"].map((c) => (
                <span
                  key={c}
                  className="rounded-sm border border-line bg-paper/60 px-2 py-0.5 font-mono text-[10px] text-ink"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section>
        <p className="eyebrow mb-3">What the system does</p>
        <div className="grid gap-px overflow-hidden rounded-sm border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap) => (
            <Link
              key={cap.code}
              href={cap.href}
              className="group flex flex-col bg-surface p-5 transition-colors hover:bg-paper/50"
            >
              <span className="font-mono text-[11px] text-accent">{cap.code}</span>
              <span className="mt-2 font-display text-[15px] font-bold tracking-tight">
                {cap.title}
              </span>
              <span className="mt-1.5 flex-1 text-[13px] leading-relaxed text-slate">
                {cap.body}
              </span>
              <span className="mt-3 font-display text-[12px] font-semibold text-accent group-hover:underline">
                {cap.cta} →
              </span>
            </Link>
          ))}
        </div>
      </section>

      <p className="text-[11px] text-slate">
        All lender figures are indicative, public-sourced approximations — not any lender&apos;s live
        or internal policy.
      </p>
    </div>
  );
}

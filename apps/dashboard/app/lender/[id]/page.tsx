import Link from "next/link";
import { notFound } from "next/navigation";
import { getLender } from "@/lib/api";
import { decisionStyle } from "@/lib/decision";
import { inr, inrCompact } from "@/lib/format";
import type { Decision, LenderPolicy } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function LenderPage({ params }: { params: { id: string } }) {
  let policy: LenderPolicy;
  try {
    policy = await getLender(params.id);
  } catch {
    notFound();
  }

  return (
    <article className="mx-auto max-w-3xl">
      <Link href="/" className="font-display text-[12px] font-semibold text-accent hover:underline">
        ← Back to match
      </Link>

      <header className="mt-3 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-bold tracking-tight">{policy.lender_name}</h1>
        <span className="font-mono text-[12px] text-slate">
          {policy.lender_type} · v{policy.policy_version} · {policy.effective_date}
        </span>
      </header>

      <section className="mt-4 rounded-sm border border-accent/20 bg-accent/5 px-4 py-3">
        <p className="eyebrow text-accent">Provenance</p>
        <p className="mt-1 text-[13px] text-ink">{policy.source}</p>
        <p className="mt-2 text-[12px] italic text-slate">{policy.disclaimer}</p>
      </section>

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <KeyTerm label="Max tenure" value={`${policy.tenure.max_years} yrs`} />
        <KeyTerm label="NMI multiplier" value={`${policy.nmi_multiplier.max}×`} />
        <KeyTerm label="Loan range" value={`${inrCompact(policy.limits.min_loan)} – ${inrCompact(policy.limits.max_loan)}`} />
      </div>

      <Panel title="LTV bands">
        <table className="w-full font-mono text-[12px]">
          <thead>
            <tr className="text-left text-slate">
              <th className="py-1 font-medium">Up to loan</th>
              <th className="py-1 text-right font-medium">Max LTV</th>
            </tr>
          </thead>
          <tbody>
            {policy.ltv_bands.map((band, i) => (
              <tr key={i} className="border-t border-line">
                <td className="py-1.5">{band.up_to_amount ? inr(band.up_to_amount) : "no limit"}</td>
                <td className="py-1.5 text-right">{band.max_ltv_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="CIBIL tiers">
        <table className="w-full font-mono text-[12px]">
          <thead>
            <tr className="text-left text-slate">
              <th className="py-1 font-medium">Band</th>
              <th className="py-1 font-medium">Decision</th>
              <th className="py-1 text-right font-medium">Rate</th>
            </tr>
          </thead>
          <tbody>
            {policy.cibil_tiers.map((tier, i) => (
              <tr key={i} className="border-t border-line">
                <td className="py-1.5">
                  {tier.min_score === -1 ? "thin file" : `${tier.min_score}–${tier.max_score}`}
                </td>
                <td className="py-1.5">
                  <span className={decisionStyle[tier.decision as Decision].text}>{tier.decision}</span>
                </td>
                <td className="py-1.5 text-right">{tier.rate_pct ? `${tier.rate_pct}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <p className="mt-5 text-[11px] text-slate">
        Products: {policy.products.map((p) => p.replaceAll("_", " ").toLowerCase()).join(", ")}.
      </p>
    </article>
  );
}

function KeyTerm({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-line bg-surface px-4 py-3 shadow-card">
      <div className="eyebrow">{label}</div>
      <div className="mt-1 font-display text-lg font-semibold tnum">{value}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-5 rounded-sm border border-line bg-surface p-4 shadow-card">
      <p className="eyebrow mb-2">{title}</p>
      {children}
    </section>
  );
}

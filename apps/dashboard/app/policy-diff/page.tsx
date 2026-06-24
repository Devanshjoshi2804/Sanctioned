"use client";

import { useEffect, useState } from "react";
import { API_BASE, postPolicyDiff } from "@/lib/api";
import { decisionStyle } from "@/lib/decision";
import { inrCompact, signedInr } from "@/lib/format";
import type { DiffReport, LenderDiff } from "@/lib/types";

// Raw policy objects carry every field; we mutate them structurally for the diff.
type RawPolicy = Record<string, any>;

export default function PolicyDiffPage() {
  const [policies, setPolicies] = useState<RawPolicy[]>([]);
  const [lenderId, setLenderId] = useState("");
  const [rateBps, setRateBps] = useState("25");
  const [foirPp, setFoirPp] = useState("0");
  const [ltvPp, setLtvPp] = useState("-5");
  const [report, setReport] = useState<DiffReport | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/lenders`, { cache: "no-store" })
      .then((r) => r.json())
      .then((data: RawPolicy[]) => {
        setPolicies(data);
        setLenderId(data[0]?.lender_id ?? "");
      })
      .catch((e) => setError(String(e)));
  }, []);

  const run = async () => {
    setPending(true);
    setError(null);
    try {
      const head = applyShift(policies, lenderId, Number(rateBps), Number(foirPp), Number(ltvPp));
      setReport(await postPolicyDiff(head));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Diff failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-5">
        <p className="eyebrow">Regression safety</p>
        <h1 className="mt-1 font-display text-2xl font-bold tracking-tight">
          What does a rate-card change do to the funnel?
        </h1>
        <p className="mt-1 max-w-2xl text-[13px] text-slate">
          Shift one lender&apos;s terms and replay the full golden persona set through both versions.
          The report shows who flips, how sanctions move, and which constraint starts binding.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3 rounded-sm border border-line bg-surface p-4 shadow-card">
        <Control label="Lender">
          <select
            value={lenderId}
            onChange={(e) => setLenderId(e.target.value)}
            className="rounded-sm border border-line bg-surface px-2 py-1.5 text-[13px]"
          >
            {policies.map((p) => (
              <option key={p.lender_id} value={p.lender_id}>
                {p.lender_name}
              </option>
            ))}
          </select>
        </Control>
        <Control label="Rate shift (bps)">
          <NumInput value={rateBps} onChange={setRateBps} />
        </Control>
        <Control label="FOIR shift (pp)">
          <NumInput value={foirPp} onChange={setFoirPp} />
        </Control>
        <Control label="LTV shift (pp)">
          <NumInput value={ltvPp} onChange={setLtvPp} />
        </Control>
        <button
          type="button"
          onClick={run}
          disabled={pending || !lenderId}
          data-testid="run-diff"
          className="rounded-sm bg-accent px-4 py-2 font-display text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-60"
        >
          {pending ? "Replaying…" : "Run impact"}
        </button>
      </div>

      {error && (
        <p className="mt-4 rounded-sm border border-reject/30 bg-reject/5 px-4 py-3 font-mono text-[12px] text-reject">
          {error}
        </p>
      )}

      {report && <Report report={report} />}
    </div>
  );
}

function Report({ report }: { report: DiffReport }) {
  return (
    <section className="mt-6" data-testid="diff-report">
      <p className="text-[13px] text-slate">
        Replayed <span className="font-mono text-ink">{report.persona_count}</span> personas.{" "}
        {report.has_changes ? (
          <span className="text-ink">
            <span className="font-mono">{report.total_decision_flips}</span> decision flip(s).
          </span>
        ) : (
          <span className="text-approve">No matching impact.</span>
        )}
      </p>

      <div className="mt-3 overflow-hidden rounded-sm border border-line bg-surface shadow-card">
        <table className="w-full text-[12px]">
          <thead className="border-b border-line text-left">
            <tr className="text-slate">
              <th className="px-3 py-2 font-medium">Lender</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 text-right font-medium">Flips</th>
              <th className="px-3 py-2 text-right font-medium">Sanctions Δ</th>
              <th className="px-3 py-2 text-right font-medium">Avg Δ</th>
              <th className="px-3 py-2 text-right font-medium">Binding Δ</th>
            </tr>
          </thead>
          <tbody>
            {report.lender_diffs.map((d) => (
              <LenderDiffRow key={d.lender_id} diff={d} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LenderDiffRow({ diff }: { diff: LenderDiff }) {
  const changed = diff.status === "changed";
  return (
    <tr className="border-b border-line/70 last:border-0" data-lender-id={diff.lender_id}>
      <td className="px-3 py-2 font-mono">{diff.lender_id}</td>
      <td className={`px-3 py-2 ${changed ? "text-refer" : "text-slate"}`}>{diff.status}</td>
      <td className="px-3 py-2 text-right font-mono tnum">{diff.decision_flips}</td>
      <td className="px-3 py-2 text-right font-mono tnum">{diff.sanction_changed}</td>
      <td className="px-3 py-2 text-right font-mono tnum">
        {diff.sanction_changed ? signedInr(diff.avg_delta) : "—"}
      </td>
      <td className="px-3 py-2 text-right font-mono tnum">{diff.binding_changes}</td>
    </tr>
  );
}

function applyShift(
  policies: RawPolicy[],
  lenderId: string,
  rateBps: number,
  foirPp: number,
  ltvPp: number,
): RawPolicy[] {
  return policies.map((policy) => {
    if (policy.lender_id !== lenderId) return policy;
    const next = structuredClone(policy);
    for (const cls of ["salaried", "self_employed"]) {
      for (const band of next.foir?.[cls] ?? []) {
        band.cap_pct = String(clamp(Number(band.cap_pct) + foirPp, 1, 70));
      }
    }
    for (const band of next.ltv_bands ?? []) {
      band.max_ltv_pct = String(clamp(Number(band.max_ltv_pct) + ltvPp, 1, 90));
    }
    for (const tier of next.cibil_tiers ?? []) {
      if (tier.rate_pct !== null) {
        tier.rate_pct = String((Number(tier.rate_pct) + rateBps / 100).toFixed(2));
      }
    }
    return next;
  });
}

function clamp(value: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, value));
}

function Control({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-[11px] text-slate">{label}</span>
      {children}
    </label>
  );
}

function NumInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-24 rounded-sm border border-line bg-surface px-2 py-1.5 font-mono text-[13px] tnum outline-none focus:border-accent focus:ring-1 focus:ring-accent"
    />
  );
}

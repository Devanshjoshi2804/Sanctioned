"use client";

import { useState } from "react";
import { BorrowerForm } from "@/components/BorrowerForm";
import { MatchGrid } from "@/components/MatchGrid";
import { postMatch } from "@/lib/api";
import { inrCompact, rate } from "@/lib/format";
import type { MatchResult } from "@/lib/types";

export default function MatchPage() {
  const [result, setResult] = useState<MatchResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (profile: unknown) => {
    setPending(true);
    setError(null);
    try {
      setResult(await postMatch(profile));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Match failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
      <aside className="lg:sticky lg:top-6 lg:self-start">
        <p className="eyebrow mb-1">Borrower</p>
        <div className="rounded-sm border border-line bg-surface p-4 shadow-card">
          <BorrowerForm onSubmit={run} pending={pending} />
        </div>
      </aside>

      <section>
        <header className="mb-5">
          <p className="eyebrow">Eligibility run</p>
          <h1 className="mt-1 max-w-xl font-display text-2xl font-bold leading-tight tracking-tight">
            Which lenders fund this borrower — and the exact reason for every verdict.
          </h1>
        </header>

        {error && (
          <div className="rounded-sm border border-reject/30 bg-reject/5 px-4 py-3 text-[13px] text-reject" role="alert">
            <p className="font-semibold">Could not reach the matching engine.</p>
            <p className="mt-0.5 font-mono text-[11px]">{error}</p>
          </div>
        )}

        {!result && !error && (
          <div className="rounded-sm border border-dashed border-line bg-surface/50 px-6 py-16 text-center">
            <p className="font-display text-sm font-semibold text-ink">No run yet</p>
            <p className="mx-auto mt-1 max-w-sm text-[13px] text-slate">
              Adjust the borrower on the left and run the match. Every lender returns a verdict, a
              max sanction, and a full reason trace.
            </p>
          </div>
        )}

        {result && (
          <>
            <SummaryStrip result={result} />
            <div className="mt-5 rounded-sm border border-line bg-surface p-3 shadow-card">
              <MatchGrid result={result} />
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function SummaryStrip({ result }: { result: MatchResult }) {
  const { summary } = result;
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-line bg-line sm:grid-cols-4" data-testid="summary">
      <Stat label="Eligible lenders" value={`${summary.eligible_count} / ${result.results.length}`} />
      <Stat label="Best rate" value={rate(summary.best_rate)} />
      <Stat label="Top sanction" value={inrCompact(summary.max_sanction_overall)} />
      <Stat label="Top lender" value={summary.top_lender_id ?? "—"} mono />
    </dl>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-surface px-4 py-3">
      <dt className="eyebrow">{label}</dt>
      <dd className={`mt-1 text-lg font-semibold tnum ${mono ? "font-mono text-base" : "font-display"}`}>
        {value}
      </dd>
    </div>
  );
}

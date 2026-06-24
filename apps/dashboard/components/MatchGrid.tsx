"use client";

import { useState } from "react";
import Link from "next/link";
import { decisionStyle } from "@/lib/decision";
import { inr, inrCompact, rate, signedInr } from "@/lib/format";
import type { EligibilityResult, MatchResult } from "@/lib/types";
import { DecisionBadge } from "./DecisionBadge";
import { ReasonLedger } from "./ReasonLedger";

export function MatchGrid({ result }: { result: MatchResult }) {
  return (
    <section data-testid="match-grid">
      <div className="grid grid-cols-[16px_1.4fr_1fr_0.7fr_0.9fr_0.9fr_auto] items-center gap-x-3 border-b border-line px-3 pb-2">
        <span />
        <span className="eyebrow">Lender</span>
        <span className="eyebrow text-right">Max sanction</span>
        <span className="eyebrow text-right">Rate</span>
        <span className="eyebrow text-right">EMI</span>
        <span className="eyebrow">Binds on</span>
        <span className="eyebrow">Verdict</span>
      </div>
      <ol className="divide-y divide-line">
        {result.results.map((item) => (
          <LenderRow key={item.lender_id} item={item} />
        ))}
      </ol>
    </section>
  );
}

function LenderRow({ item }: { item: EligibilityResult }) {
  const [open, setOpen] = useState(false);
  const style = decisionStyle[item.decision];

  return (
    <li data-testid="lender-row" data-lender-id={item.lender_id} data-decision={item.decision}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="grid w-full grid-cols-[16px_1.4fr_1fr_0.7fr_0.9fr_0.9fr_auto] items-center gap-x-3 px-3 py-3 text-left hover:bg-paper/60"
      >
        <span className={`h-9 w-1 rounded-sm ${style.spine}`} aria-hidden />
        <span className="min-w-0">
          <span className="block truncate font-display text-sm font-semibold">{item.lender_name}</span>
          <span className="block font-mono text-[11px] text-slate">{item.lender_id}</span>
        </span>
        <span className="text-right font-mono text-sm tnum" data-testid="sanction">
          {inr(item.max_sanction)}
        </span>
        <span className="text-right font-mono text-sm tnum">{rate(item.indicative_rate_pct)}</span>
        <span className="text-right font-mono text-sm tnum">{inr(item.indicative_emi)}</span>
        <span className="font-mono text-[11px] text-slate">{item.binding_constraint ?? "—"}</span>
        <span className="flex items-center gap-2">
          <DecisionBadge decision={item.decision} />
          <span className={`text-slate transition-transform ${open ? "rotate-90" : ""}`} aria-hidden>
            ›
          </span>
        </span>
      </button>

      {open && (
        <div className="border-t border-line bg-paper/40 pb-3">
          {(item.warnings.length > 0 || item.monthly_saving || item.net_benefit_note) && (
            <div className="space-y-1 px-4 pt-3">
              {item.monthly_saving && (
                <p className="text-[12px] text-ink" data-testid="monthly-saving">
                  Indicative monthly saving:{" "}
                  <span className="font-mono font-medium text-approve">{signedInr(item.monthly_saving)}</span>
                </p>
              )}
              {item.net_benefit_note && <p className="text-[12px] text-slate">{item.net_benefit_note}</p>}
              {item.warnings.map((warning) => (
                <p key={warning} className="text-[12px] text-refer">
                  ⚠ {warning}
                </p>
              ))}
            </div>
          )}
          <div className="mt-2 grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-line bg-line text-[11px] sm:grid-cols-4 mx-4">
            <Bound label="FOIR" value={item.bounds.foir} />
            <Bound label="LTV" value={item.bounds.ltv} />
            <Bound label="Multiplier" value={item.bounds.multiplier} />
            <Bound label="Lender cap" value={item.bounds.lender_cap} />
          </div>
          <div className="mt-3">
            <div className="flex items-center justify-between px-4">
              <span className="eyebrow">Reason trace</span>
              <Link
                href={`/lender/${item.lender_id}`}
                className="font-display text-[11px] font-semibold text-accent hover:underline"
              >
                View policy →
              </Link>
            </div>
            <div className="mt-1 border-t border-line bg-surface">
              <ReasonLedger reasons={item.reasons} />
            </div>
          </div>
        </div>
      )}
    </li>
  );
}

function Bound({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface px-3 py-2">
      <div className="eyebrow">{label}</div>
      <div className="mt-0.5 font-mono text-[12px] tnum">{inrCompact(value)}</div>
    </div>
  );
}

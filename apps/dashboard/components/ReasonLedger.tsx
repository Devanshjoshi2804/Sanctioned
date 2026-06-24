import type { ReasonTrace } from "@/lib/types";

// The signature element: the reason trace rendered as a compliance printout.
// Every evaluated rule is one monospace line — a glyph, the code, the borrower's
// value against the policy threshold, and a plain-language detail. This is the
// "why didn't this customer match?" answer, auditable line by line.
export function ReasonLedger({ reasons }: { reasons: ReasonTrace[] }) {
  return (
    <ol className="divide-y divide-line/70 font-mono text-[12px]" data-testid="reason-ledger">
      {reasons.map((trace, index) => (
        <li key={`${trace.code}-${index}`} className="flex gap-3 px-4 py-2" data-trace-code={trace.code}>
          <span
            aria-hidden
            className={`mt-px select-none font-semibold ${trace.passed ? "text-approve" : "text-reject"}`}
          >
            {trace.passed ? "✓" : "✕"}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="font-semibold text-ink">{trace.code}</span>
              <span className="text-slate">{trace.rule}</span>
            </div>
            <p className="mt-0.5 text-ink/80">{trace.detail}</p>
            <p className="mt-0.5 text-[11px] text-slate">
              value <span className="text-ink">{trace.value}</span> · threshold{" "}
              <span className="text-ink">{trace.threshold}</span>
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}

import { decisionStyle } from "@/lib/decision";
import type { Decision } from "@/lib/types";

export function DecisionBadge({ decision }: { decision: Decision }) {
  const style = decisionStyle[decision];
  return (
    <span
      className={`inline-flex items-center rounded-sm px-1.5 py-0.5 font-display text-[11px] font-semibold uppercase tracking-wide ${style.chip}`}
      data-decision={decision}
    >
      {style.label}
    </span>
  );
}

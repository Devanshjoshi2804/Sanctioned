// Display formatting. The engine sends exact Decimal strings; we parse only at
// the edge, for rendering.

export function inr(value: string | null): string {
  if (value === null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

// Compact Indian rendering for big figures: ₹51.0L, ₹1.2Cr.
export function inrCompact(value: string | null): string {
  if (value === null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  if (n >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(2)}Cr`;
  if (n >= 1_00_000) return `₹${(n / 1_00_000).toFixed(1)}L`;
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function rate(value: string | null): string {
  if (value === null || value === "") return "—";
  return `${value}%`;
}

export function signedInr(value: string): string {
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  const sign = n >= 0 ? "+" : "−";
  return `${sign}₹${Math.abs(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

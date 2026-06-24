// Response shapes mirroring the FastAPI/engine models. Money and rates arrive as
// strings (exact Decimal) and are parsed only for display.

export type Decision = "APPROVE" | "REFER" | "REJECT";

export interface ReasonTrace {
  code: string;
  rule: string;
  passed: boolean;
  value: string;
  threshold: string;
  detail: string;
}

export interface Bounds {
  foir: string;
  ltv: string;
  multiplier: string;
  lender_cap: string;
}

export interface EligibilityResult {
  lender_id: string;
  lender_name: string;
  decision: Decision;
  eligible: boolean;
  max_sanction: string;
  binding_constraint: string | null;
  indicative_rate_pct: string | null;
  indicative_emi: string | null;
  bounds: Bounds;
  effective_tenure_years: number;
  reasons: ReasonTrace[];
  warnings: string[];
  monthly_saving: string | null;
  net_benefit_note: string | null;
}

export interface MatchSummary {
  eligible_count: number;
  best_rate: string | null;
  max_sanction_overall: string;
  top_lender_id: string | null;
}

export interface MatchResult {
  generated_at: string;
  results: EligibilityResult[];
  summary: MatchSummary;
}

export interface LenderPolicy {
  lender_id: string;
  lender_name: string;
  lender_type: string;
  policy_version: string;
  effective_date: string;
  source: string;
  disclaimer: string;
  products: string[];
  tenure: { max_years: number };
  nmi_multiplier: { min: string; max: string };
  ltv_bands: { up_to_amount: string | null; max_ltv_pct: string }[];
  cibil_tiers: { min_score: number; max_score: number; decision: Decision; rate_pct: string | null }[];
  limits: { min_loan: string; max_loan: string };
}

export interface LenderDiff {
  lender_id: string;
  status: "changed" | "unchanged" | "added" | "removed";
  personas: number;
  decision_flips: number;
  flip_breakdown: Record<string, number>;
  sanction_changed: number;
  avg_delta: string;
  median_delta: string;
  binding_changes: number;
  largest_movers: {
    persona_index: number;
    base_sanction: string;
    head_sanction: string;
    delta: string;
  }[];
}

export interface DiffReport {
  persona_count: number;
  total_decision_flips: number;
  has_changes: boolean;
  lender_diffs: LenderDiff[];
}

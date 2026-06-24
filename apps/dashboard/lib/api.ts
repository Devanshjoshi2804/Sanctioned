// Thin client for the sanctioned API. Base URL is configurable so the dashboard
// can point at a local engine or a deployed one.

import type { DiffReport, LenderPolicy, MatchResult } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return (await response.json()) as T;
}

export function postMatch(profile: unknown): Promise<MatchResult> {
  return request<MatchResult>("/match", { method: "POST", body: JSON.stringify(profile) });
}

export function getLenders(): Promise<LenderPolicy[]> {
  return request<LenderPolicy[]>("/lenders");
}

export function getLender(id: string): Promise<LenderPolicy> {
  return request<LenderPolicy>(`/lenders/${id}`);
}

export function postPolicyDiff(headPolicies: unknown[]): Promise<DiffReport> {
  return request<DiffReport>("/policy-diff", {
    method: "POST",
    body: JSON.stringify({ head_policies: headPolicies }),
  });
}

export interface IngestResult {
  autofill: { net_monthly_income: string; existing_monthly_obligations: string };
  derived: { salary_regularity: string; months_observed: number; disclaimer: string };
}

export function postIngestSandbox(): Promise<IngestResult> {
  return request<IngestResult>("/ingest/sandbox", { method: "POST", body: "{}" });
}

export interface AskResult {
  question: string;
  answer: string;
  backend: string;
  citations: { citation: string; source: string; section: string; score: number }[];
}

export function postAsk(question: string): Promise<AskResult> {
  return request<AskResult>("/ask", { method: "POST", body: JSON.stringify({ question }) });
}

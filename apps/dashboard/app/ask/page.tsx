"use client";

import { useState } from "react";
import { postAsk } from "@/lib/api";
import type { AskResult } from "@/lib/api";

const SUGGESTIONS = [
  "Which lenders accept self-employed borrowers with two years of ITR?",
  "Who offers the lowest rate for a prime borrower?",
  "Do any lenders consider a thin credit file?",
  "What is the maximum LTV on a property above 75 lakh?",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (q: string) => {
    const text = q.trim();
    if (!text) return;
    setQuestion(text);
    setPending(true);
    setError(null);
    try {
      setResult(await postAsk(text));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-5">
        <p className="eyebrow">Ops copilot</p>
        <h1 className="mt-1 font-display text-2xl font-bold tracking-tight">
          Ask the policy panel — answered only from the sources.
        </h1>
        <p className="mt-1 max-w-2xl text-[13px] text-slate">
          The copilot retrieves from the lender policies and the runbook and answers with
          citations. It never answers from the model&apos;s own knowledge.
        </p>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="flex gap-2"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. which lenders fund under-construction property?"
          data-testid="ask-input"
          className="flex-1 rounded-sm border border-line bg-surface px-3 py-2 text-[14px] outline-none focus:border-accent focus:ring-1 focus:ring-accent"
        />
        <button
          type="submit"
          disabled={pending}
          data-testid="ask-submit"
          className="rounded-sm bg-accent px-4 py-2 font-display text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-60"
        >
          {pending ? "Asking…" : "Ask"}
        </button>
      </form>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => ask(s)}
            className="rounded-sm border border-line bg-surface px-2 py-1 text-[11px] text-slate hover:border-accent hover:text-ink"
          >
            {s}
          </button>
        ))}
      </div>

      {error && (
        <p className="mt-4 rounded-sm border border-reject/30 bg-reject/5 px-4 py-3 font-mono text-[12px] text-reject">
          {error}
        </p>
      )}

      {result && (
        <section className="mt-5 rounded-sm border border-line bg-surface p-4 shadow-card" data-testid="ask-answer">
          <div className="mb-2 flex items-center gap-2">
            <span className="eyebrow">Answer</span>
            <span className="rounded-sm bg-paper px-1.5 py-0.5 font-mono text-[10px] uppercase text-slate">
              {result.backend}
            </span>
          </div>
          <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-ink">{result.answer}</p>
          <div className="mt-3 border-t border-line pt-3">
            <p className="eyebrow mb-1.5">Sources</p>
            <ul className="flex flex-wrap gap-1.5">
              {result.citations.map((c) => (
                <li
                  key={c.citation}
                  className="rounded-sm border border-line bg-paper/60 px-2 py-1 font-mono text-[11px] text-ink"
                  title={c.source}
                >
                  {c.citation}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}

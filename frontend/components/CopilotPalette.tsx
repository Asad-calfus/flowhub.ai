"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Command, Send, Sparkles, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { SentimentBadge } from "@/components/Badges";
import { formatConfidence } from "@/lib/formatters";
import type { CopilotAnswerOut } from "@/lib/types";

/** Global Cmd+K (Ctrl+K on non-Mac) AI Copilot overlay - accessible from any page, not
 * just the dedicated /copilot page. Always asks in dry-run/local mode (deterministic,
 * free) - use the full /copilot page for the live-LLM option. */
export function CopilotPalette() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState<CopilotAnswerOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 0);
    } else {
      setQuestion("");
      setResult(null);
      setError(null);
    }
  }, [open]);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || asking) return;
    setAsking(true);
    setError(null);
    try {
      setResult(await api.askCopilot({ question: q }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to get an answer.");
    } finally {
      setAsking(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-slate-900/40 p-4 pt-24" onClick={() => setOpen(false)}>
      <div className="w-full max-w-xl rounded-xl border border-slate-200 bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleAsk} className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
          <Sparkles className="h-4 w-4 shrink-0 text-brand-600" />
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about your feedback…"
            className="flex-1 text-sm outline-none placeholder:text-slate-400"
            maxLength={500}
          />
          <button type="submit" disabled={asking || !question.trim()} aria-label="Ask" className="text-slate-400 hover:text-brand-600 disabled:opacity-40">
            <Send className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setOpen(false)} aria-label="Close" className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </form>

        <div className="max-h-96 overflow-y-auto p-4">
          {asking && <p className="text-sm text-slate-400">Thinking…</p>}
          {!asking && error && <p className="text-sm text-rose-600">{error}</p>}
          {!asking && !error && !result && (
            <p className="flex items-center gap-1.5 text-xs text-slate-400">
              <Command className="h-3 w-3" />K to toggle · dry-run/local answers only -{" "}
              <Link href="/copilot" className="text-brand-600 hover:underline" onClick={() => setOpen(false)}>
                open full Copilot
              </Link>{" "}
              for live LLM answers
            </p>
          )}
          {!asking && result && (
            <div className="space-y-3">
              <p className="text-sm leading-relaxed text-slate-700">{result.answer}</p>
              {result.sources.length > 0 && (
                <ul className="space-y-1.5 border-t border-slate-100 pt-2">
                  {result.sources.map((s) => (
                    <li key={s.feedback_id} className="flex items-start justify-between gap-3 text-xs">
                      <div>
                        <Link href={`/feedback/${s.feedback_id}`} className="font-medium text-brand-600 hover:underline" onClick={() => setOpen(false)}>
                          {s.feedback_id}
                        </Link>
                        <span className="ml-2 text-slate-500">{s.text_preview}</span>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <SentimentBadge sentiment={s.sentiment} />
                        <span className="whitespace-nowrap text-slate-400">{formatConfidence(s.similarity_score)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

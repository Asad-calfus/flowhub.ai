"use client";

import { useState } from "react";
import Link from "next/link";
import { Send, Sparkles } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { ProcessingModeToggle, type ProcessingMode } from "@/components/ProcessingModeToggle";
import { SentimentBadge } from "@/components/Badges";
import { formatConfidence } from "@/lib/formatters";
import type { CopilotAnswerOut } from "@/lib/types";

interface Turn {
  question: string;
  result: CopilotAnswerOut | null;
  error: string | null;
}

export default function CopilotPage() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<ProcessingMode>("local");
  const [asking, setAsking] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || asking) return;

    setAsking(true);
    try {
      const result = await api.askCopilot({ question: q, live: mode === "api" });
      setTurns((prev) => [{ question: q, result, error: null }, ...prev]);
    } catch (err) {
      setTurns((prev) => [{ question: q, result: null, error: err instanceof ApiError ? err.message : "Failed to get an answer." }, ...prev]);
    } finally {
      setAsking(false);
      setQuestion("");
    }
  };

  return (
    <div>
      <PageHeader
        title="AI Copilot"
        description="Ask a question in plain English - retrieval finds the closest stored feedback, then it's worded into an answer. Every answer only draws on the feedback shown as its source."
      />
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <form onSubmit={handleAsk} className="card space-y-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Sparkles className="h-4 w-4" />
            </span>
            <h2 className="text-sm font-semibold text-slate-800">Ask about your feedback</h2>
          </div>

          <ProcessingModeToggle
            value={mode}
            onChange={setMode}
            localDescription="A deterministic summary of the retrieved feedback"
            apiDescription="An AI-written answer grounded in the retrieved feedback"
          />

          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Are customers having trouble with SSO login?"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
              maxLength={500}
            />
            <button type="submit" disabled={asking || !question.trim()} className="btn-primary">
              <Send className="h-4 w-4" /> {asking ? "Asking…" : "Ask"}
            </button>
          </div>
        </form>

        <div className="space-y-4">
          {turns.length === 0 && <p className="text-sm text-slate-400">Ask a question above to see an answer with linked source feedback.</p>}
          {turns.map((turn, i) => (
            <div key={i} className="card space-y-3">
              <p className="text-sm font-semibold text-slate-800">{turn.question}</p>
              {turn.error && <p className="text-sm text-rose-600">{turn.error}</p>}
              {turn.result && (
                <>
                  <p className="text-sm leading-relaxed text-slate-700">{turn.result.answer}</p>
                  <p className="text-xs text-slate-400">Model: {turn.result.model_name}</p>
                  {turn.result.sources.length > 0 && (
                    <div className="border-t border-slate-100 pt-2">
                      <p className="mb-1.5 text-xs font-medium text-slate-500">Sources</p>
                      <ul className="space-y-1.5">
                        {turn.result.sources.map((s) => (
                          <li key={s.feedback_id} className="flex items-start justify-between gap-3 text-xs">
                            <div>
                              <Link href={`/feedback/${s.feedback_id}`} className="font-medium text-brand-600 hover:underline">
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
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

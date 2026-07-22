"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, CheckCircle2, Cog } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { FeedbackCsvImport } from "@/components/FeedbackCsvImport";
import { ProcessingModeToggle, type ProcessingMode } from "@/components/ProcessingModeToggle";
import { ErrorState } from "@/components/States";
import type { ImportSummary } from "@/lib/types";

export default function GetStartedPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [mode, setMode] = useState<ProcessingMode>("local");
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProcess = async () => {
    setProcessing(true);
    setError(null);
    try {
      // "local" = free rule-based classifier, never calls an LLM.
      // "api" = real OpenAI call, opt-in only - see PROJECT_CONTEXT.md cost-safety notes.
      await api.runBatchAnalysis(mode === "api" ? "llm" : "baseline", mode === "api");
      await api.runBatchRetrieval(); // free, local - so weekly reports never show the
      // "not run through context-match retrieval yet" data limitation for this workspace
      await api.recomputeThemes(); // deterministic, local, no LLM
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to process your data.");
      setProcessing(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Get started"
        description="Upload your feedback CSV, then process it to build your dashboard."
      />
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <FeedbackCsvImport onImported={setSummary} />

        {error && <ErrorState message={error} onRetry={handleProcess} />}

        {summary && summary.feedback_imported > 0 && !error && (
          <div className="card space-y-4">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <CheckCircle2 className="h-4 w-4" />
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-800">Ready to process</p>
                <p className="text-xs text-slate-500">
                  Classifies and clusters your {summary.feedback_imported} imported record
                  {summary.feedback_imported === 1 ? "" : "s"} into themes.
                </p>
              </div>
            </div>

            <ProcessingModeToggle
              value={mode}
              onChange={setMode}
              localDescription="Rule-based classification"
              apiDescription="LLM classification"
            />

            <button onClick={handleProcess} disabled={processing} className="btn-primary">
              {processing ? (
                <>
                  <Cog className="h-4 w-4 animate-spin" /> Processing…
                </>
              ) : (
                <>
                  Process my data <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

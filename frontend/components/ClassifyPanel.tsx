"use client";

import { useEffect, useState } from "react";
import { Cog, Sparkles } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { ProcessingModeToggle, type ProcessingMode } from "@/components/ProcessingModeToggle";
import type { BatchAnalysisResponse, CostEstimate } from "@/lib/types";

interface ClassifyPanelProps {
  /** Called after a batch classification run completes, so the caller can refresh its list. */
  onDone: () => void;
}

/** Review-and-classify step shown after CSV import: runs over every pending (unclassified)
 * feedback record in the workspace - not a sample, not just the gold set - and shows the
 * estimated cost up front when the real LLM API is chosen, before anything is spent. */
export function ClassifyPanel({ onDone }: ClassifyPanelProps) {
  const [mode, setMode] = useState<ProcessingMode>("local");
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [loadingEstimate, setLoadingEstimate] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BatchAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingEstimate(true);
    api
      .estimateAnalysisCost()
      .then((est) => !cancelled && setEstimate(est))
      .catch(() => !cancelled && setEstimate(null))
      .finally(() => !cancelled && setLoadingEstimate(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const pendingCount = estimate?.pending_count ?? 0;

  const handleClassify = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.runBatchAnalysis(mode === "api" ? "llm" : "baseline", mode === "api");
      setResult(res);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Classification failed.");
    } finally {
      setRunning(false);
    }
  };

  if (!loadingEstimate && pendingCount === 0 && !result) return null;

  return (
    <div className="card space-y-3" data-testid="classify-panel">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <Sparkles className="h-4 w-4" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Review &amp; classify feedback</h2>
          <p className="text-xs text-slate-500">
            {loadingEstimate
              ? "Checking pending feedback…"
              : `${pendingCount} record${pendingCount === 1 ? "" : "s"} awaiting classification (the whole backlog, not a sample).`}
          </p>
        </div>
      </div>

      {pendingCount > 0 && (
        <>
          <ProcessingModeToggle
            value={mode}
            onChange={setMode}
            localDescription="Rule-based classification"
            apiDescription="LLM classification"
          />

          {mode === "api" && estimate && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Estimated cost to classify all <strong>{pendingCount}</strong> pending record
              {pendingCount === 1 ? "" : "s"} with <strong>{estimate.model}</strong>:{" "}
              <strong>${estimate.estimated_cost_usd?.toFixed(4)}</strong> (rough pre-flight estimate, not
              billing-exact).
            </p>
          )}

          <button onClick={handleClassify} disabled={running} className="btn-primary">
            {running ? (
              <>
                <Cog className="h-4 w-4 animate-spin" /> Classifying…
              </>
            ) : (
              `Classify ${pendingCount} record${pendingCount === 1 ? "" : "s"}`
            )}
          </button>
        </>
      )}

      {error && <p className="text-xs text-rose-600">{error}</p>}

      {result && (
        <p className="text-xs text-emerald-700">
          Done: {result.succeeded} classified, {result.failed} failed, {result.skipped} skipped.
        </p>
      )}
    </div>
  );
}

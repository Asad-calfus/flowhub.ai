"use client";

import { useState } from "react";
import { Cog, SearchCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { RetrievalBatchResponse } from "@/lib/types";

interface RetrievalPanelProps {
  /** Called after a batch retrieval run completes, so the caller can refresh its list. */
  onDone: () => void;
}

/** Runs context-matching (similar-feedback + known-bug/feature-request/release matching)
 * over every feedback record in the workspace that hasn't been checked yet - the backlog
 * that otherwise only gets processed one record at a time when someone opens its detail
 * page, and which shows up as a weekly report "data limitation" until it's run. */
export function RetrievalPanel({ onDone }: RetrievalPanelProps) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RetrievalBatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.runBatchRetrieval();
      setResult(res);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Context matching failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="card space-y-3" data-testid="retrieval-panel">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <SearchCheck className="h-4 w-4" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Run context matching</h2>
          <p className="text-xs text-slate-500">
            Checks every not-yet-checked record against similar feedback and known bugs/feature requests/releases -
            free and local, no API calls. Without this, those records stay out of the weekly report&apos;s
            known-bug/new-issue counts.
          </p>
        </div>
      </div>

      <button onClick={handleRun} disabled={running} className="btn-primary">
        {running ? (
          <>
            <Cog className="h-4 w-4 animate-spin" /> Checking…
          </>
        ) : (
          "Run context matching"
        )}
      </button>

      {error && <p className="text-xs text-rose-600">{error}</p>}

      {result && (
        <p className="text-xs text-emerald-700">
          Done: checked {result.requested} record{result.requested === 1 ? "" : "s"} ({result.succeeded} succeeded,{" "}
          {result.failed} failed).
        </p>
      )}
    </div>
  );
}

"use client";

import { useRef, useState } from "react";
import { CheckCircle2, TriangleAlert, UploadCloud } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { ImportSummary } from "@/lib/types";

interface FeedbackCsvImportProps {
  onImported: (summary: ImportSummary) => void;
}

const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10MB - generous for a demo dataset, cheap guard against pasting the wrong file

export function FeedbackCsvImport({ onImported }: FeedbackCsvImportProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ImportSummary | null>(null);

  const reset = () => {
    setFileName(null);
    setError(null);
    setSummary(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSummary(null);
    setError(null);

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please choose a .csv file.");
      setFileName(null);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setError("That file is larger than 10MB - please split it before uploading.");
      setFileName(null);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    setFileName(file.name);
    setUploading(true);
    try {
      const result = await api.importFeedbackCsv(file);
      setSummary(result);
      onImported(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to import CSV.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card space-y-3" data-testid="feedback-csv-import">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <UploadCloud className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Import feedback from CSV</h2>
            <p className="text-xs text-slate-500">
              Only <code className="rounded bg-slate-100 px-1">feedback_text</code> is required. Optional columns:
              feedback_id, source, created_at, customer_id, customer_tier, product_version, rating, language. Rows with an
              existing feedback_id are skipped, not duplicated - safe to re-upload.
            </p>
          </div>
        </div>
        <label className="btn-primary shrink-0 cursor-pointer">
          {uploading ? "Uploading…" : "Choose CSV file"}
          <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={handleFileChange} disabled={uploading} />
        </label>
      </div>

      {fileName && !error && <p className="pl-12 text-xs text-slate-500">Selected: {fileName}</p>}

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {summary && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          <p className="flex items-start gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Imported <strong>{summary.feedback_imported}</strong> new feedback record{summary.feedback_imported === 1 ? "" : "s"}
              {summary.feedback_skipped > 0 && <> ({summary.feedback_skipped} skipped as duplicates)</>}.
            </span>
          </p>
          {summary.errors.length > 0 && (
            <ul className="mt-2 list-inside list-disc pl-6 text-amber-800">
              {summary.errors.map((msg, i) => (
                <li key={i}>{msg}</li>
              ))}
            </ul>
          )}
          <button onClick={reset} className="mt-2 pl-6 text-xs font-medium text-emerald-700 underline">
            Upload another file
          </button>
        </div>
      )}
    </div>
  );
}

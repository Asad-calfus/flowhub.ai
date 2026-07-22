"use client";

import { useState } from "react";
import { Check, History, Pencil, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/formatters";
import type { AnalysisOut, Category, CorrectableField, CorrectionOut, FeedbackType, ProductModule, Sentiment, Urgency } from "@/lib/types";

const FIELD_OPTIONS: Record<CorrectableField, string[]> = {
  feedback_type: [
    "Bug report",
    "Feature request",
    "Usability issue",
    "Performance issue",
    "Service complaint",
    "Praise",
    "Question",
    "Other",
  ] satisfies FeedbackType[],
  category: ["Technical Issue", "Product Feedback", "Support Experience", "Positive Feedback", "Inquiry", "Other"] satisfies Category[],
  product_module: [
    "Authentication",
    "Dashboard",
    "Task Management",
    "Notifications",
    "Billing",
    "Integrations",
    "Reports",
    "Mobile App",
  ] satisfies ProductModule[],
  sentiment: ["Positive", "Neutral", "Negative", "Mixed"] satisfies Sentiment[],
  urgency: ["Low", "Medium", "High"] satisfies Urgency[],
};

const FIELD_LABELS: Record<CorrectableField, string> = {
  feedback_type: "Feedback type",
  category: "Category",
  product_module: "Product module",
  sentiment: "Sentiment",
  urgency: "Urgency",
};

interface FieldRowProps {
  feedbackId: string;
  field: CorrectableField;
  value: string;
  onCorrected: () => void;
}

function FieldRow({ feedbackId, field, value, onCorrected }: FieldRowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startEdit = () => {
    setDraft(value);
    setError(null);
    setEditing(true);
  };

  const save = async () => {
    if (draft === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.correctClassification(feedbackId, { field, corrected_value: draft });
      setEditing(false);
      onCorrected();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save correction.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <p className="flex items-center gap-1 text-xs text-slate-400">
        {FIELD_LABELS[field]}
        {!editing && (
          <button type="button" onClick={startEdit} aria-label={`Correct ${FIELD_LABELS[field]}`} className="text-slate-300 hover:text-brand-600">
            <Pencil className="h-3 w-3" />
          </button>
        )}
      </p>
      {editing ? (
        <div className="mt-1 flex items-center gap-1">
          <select
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="rounded-md border border-slate-300 px-1.5 py-1 text-sm focus:border-brand-400 focus:outline-none"
            autoFocus
          >
            {FIELD_OPTIONS[field].map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          <button type="button" onClick={save} disabled={saving} aria-label="Save correction" className="text-emerald-600 hover:text-emerald-700 disabled:opacity-50">
            <Check className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setEditing(false)} disabled={saving} aria-label="Cancel" className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <p className="text-sm text-slate-700">{value}</p>
      )}
      {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
    </div>
  );
}

interface CorrectionEditorProps {
  feedbackId: string;
  analysis: AnalysisOut;
  corrections: CorrectionOut[];
  onCorrected: () => void;
}

export function CorrectionEditor({ feedbackId, analysis, corrections, onCorrected }: CorrectionEditorProps) {
  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <FieldRow feedbackId={feedbackId} field="feedback_type" value={analysis.feedback_type} onCorrected={onCorrected} />
        <FieldRow feedbackId={feedbackId} field="category" value={analysis.category} onCorrected={onCorrected} />
        <FieldRow feedbackId={feedbackId} field="product_module" value={analysis.product_module} onCorrected={onCorrected} />
        <FieldRow feedbackId={feedbackId} field="sentiment" value={analysis.sentiment} onCorrected={onCorrected} />
        <FieldRow feedbackId={feedbackId} field="urgency" value={analysis.urgency} onCorrected={onCorrected} />
      </div>

      {corrections.length > 0 && (
        <div className="border-t border-slate-100 pt-3">
          <p className="mb-1.5 flex items-center gap-1 text-xs font-medium text-slate-500">
            <History className="h-3 w-3" /> Correction history
          </p>
          <ul className="space-y-1">
            {corrections.map((c) => (
              <li key={c.id} className="text-xs text-slate-500">
                <span className="font-medium text-slate-700">{FIELD_LABELS[c.field]}</span>: {c.original_value} → {c.corrected_value}
                {c.corrected_by ? ` (by ${c.corrected_by})` : ""} · {formatDateTime(c.created_at)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { CalendarClock, FileBarChart2, TriangleAlert } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { ProcessingModeToggle, type ProcessingMode } from "@/components/ProcessingModeToggle";
import type { ReportOut } from "@/lib/types";

const MODULES = [
  "Authentication",
  "Dashboard",
  "Task Management",
  "Notifications",
  "Billing",
  "Integrations",
  "Reports",
  "Mobile App",
];
const TIERS = ["Free", "Pro", "Enterprise"];

interface FormState {
  start_date: string;
  end_date: string;
  product_module: string;
  customer_tier: string;
  all_time?: boolean;
}

export interface FormErrors {
  start_date?: string;
  end_date?: string;
}

export function validateReportForm(form: FormState): FormErrors {
  const errors: FormErrors = {};
  if (form.all_time) return errors;
  if (!form.start_date) errors.start_date = "Start date is required.";
  if (!form.end_date) errors.end_date = "End date is required.";
  if (form.start_date && form.end_date && form.start_date > form.end_date) {
    errors.end_date = "End date must be on or after the start date.";
  }
  return errors;
}

interface ReportGenerationFormProps {
  onGenerated: (report: ReportOut) => void;
}

/** YYYY-MM-DD in local time (not toISOString, which shifts to UTC and can land on
 * the wrong calendar day depending on the browser's timezone). */
function toDateInputValue(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function ReportGenerationForm({ onGenerated }: ReportGenerationFormProps) {
  const [form, setForm] = useState<FormState>({
    start_date: "",
    end_date: "",
    product_module: "",
    customer_tier: "",
    all_time: false,
  });
  const [mode, setMode] = useState<ProcessingMode>("local");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const usePastWeek = () => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 6); // 7-day window (today inclusive) - matches the weekly report's period length
    setForm((f) => ({ ...f, start_date: toDateInputValue(start), end_date: toDateInputValue(end) }));
    setErrors({});
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validation = validateReportForm(form);
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;

    setSubmitting(true);
    setApiError(null);
    try {
      const report = await api.generateReport({
        start_date: form.all_time ? null : form.start_date,
        end_date: form.all_time ? null : form.end_date,
        // "local" = deterministic, template-based narrative, no LLM.
        // "api" = real OpenAI call to write the narrative - opt-in only.
        mode: mode === "api" ? "live" : "deterministic",
        product_module: form.product_module || null,
        customer_tier: form.customer_tier || null,
      });
      onGenerated(report);
    } catch (err) {
      setApiError(err instanceof ApiError ? err.message : "Failed to generate report.");
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm transition-colors focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100";

  return (
    <form onSubmit={handleSubmit} className="card space-y-3" data-testid="report-form">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <FileBarChart2 className="h-4 w-4" />
        </span>
        <h2 className="text-sm font-semibold text-slate-800">Generate a weekly report</h2>
        <button
          type="button"
          onClick={usePastWeek}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-brand-300 hover:text-brand-700"
        >
          <CalendarClock className="h-3.5 w-3.5" /> Past week
        </button>
      </div>

      <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
        <input
          type="checkbox"
          checked={form.all_time}
          onChange={(e) => setForm((f) => ({ ...f, all_time: e.target.checked }))}
          className="h-3.5 w-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-100"
        />
        All-time report (every feedback record, no date range)
      </label>

      <ProcessingModeToggle
        value={mode}
        onChange={setMode}
        localDescription="Template-based executive summary"
        apiDescription="AI-written executive summary"
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          Start date
          <input
            type="date"
            disabled={form.all_time}
            className={`${inputClass} disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400`}
            value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })}
          />
          {!form.all_time && errors.start_date && <span className="text-xs text-rose-600">{errors.start_date}</span>}
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          End date
          <input
            type="date"
            disabled={form.all_time}
            className={`${inputClass} disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400`}
            value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.target.value })}
          />
          {!form.all_time && errors.end_date && <span className="text-xs text-rose-600">{errors.end_date}</span>}
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          Product module (optional)
          <select
            className={`bg-white ${inputClass}`}
            value={form.product_module}
            onChange={(e) => setForm({ ...form, product_module: e.target.value })}
          >
            <option value="">All</option>
            {MODULES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          Customer tier (optional)
          <select
            className={`bg-white ${inputClass}`}
            value={form.customer_tier}
            onChange={(e) => setForm({ ...form, customer_tier: e.target.value })}
          >
            <option value="">All</option>
            {TIERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      </div>
      {apiError && (
        <p className="flex items-center gap-1.5 text-sm text-rose-600">
          <TriangleAlert className="h-4 w-4 shrink-0" /> {apiError}
        </p>
      )}
      <button type="submit" disabled={submitting} className="btn-primary">
        {submitting ? "Generating…" : "Generate report"}
      </button>
    </form>
  );
}

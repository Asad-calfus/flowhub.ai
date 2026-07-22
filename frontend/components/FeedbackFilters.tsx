"use client";

import { SlidersHorizontal } from "lucide-react";
import type { FeedbackListFilters } from "@/lib/types";

const SOURCES = ["Support ticket", "Survey", "App review", "Chat", "Email", "Community post"];
const SENTIMENTS = ["Positive", "Neutral", "Negative", "Mixed"];
const CATEGORIES = ["Technical Issue", "Product Feedback", "Support Experience", "Positive Feedback", "Inquiry", "Other"];
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

interface FeedbackFiltersProps {
  filters: FeedbackListFilters;
  onChange: (filters: FeedbackListFilters) => void;
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string | undefined;
  options: string[];
  onChange: (value: string | undefined) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
      {label}
      <select
        className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-700 transition-colors focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
        value={value || ""}
        onChange={(e) => onChange(e.target.value || undefined)}
      >
        <option value="">All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export function FeedbackFilters({ filters, onChange }: FeedbackFiltersProps) {
  const set = (patch: Partial<FeedbackListFilters>) => onChange({ ...filters, ...patch, page: 1 });

  return (
    <div className="card" data-testid="feedback-filters">
      <div className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Filters
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <Select label="Source" value={filters.source} options={SOURCES} onChange={(v) => set({ source: v })} />
        <Select label="Sentiment" value={filters.sentiment} options={SENTIMENTS} onChange={(v) => set({ sentiment: v })} />
        <Select label="Category" value={filters.category} options={CATEGORIES} onChange={(v) => set({ category: v })} />
        <Select label="Module" value={filters.product_module} options={MODULES} onChange={(v) => set({ product_module: v })} />
        <Select label="Customer tier" value={filters.customer_tier} options={TIERS} onChange={(v) => set({ customer_tier: v })} />
      </div>
    </div>
  );
}

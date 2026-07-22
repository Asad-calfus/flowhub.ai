import { Minus, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

const SENTIMENT_COLORS: Record<string, string> = {
  Positive: "bg-emerald-100 text-emerald-800",
  Neutral: "bg-slate-100 text-slate-700",
  Negative: "bg-rose-100 text-rose-800",
  Mixed: "bg-amber-100 text-amber-800",
};

export function SentimentBadge({ sentiment }: { sentiment: string | null | undefined }) {
  if (!sentiment) return <span className="text-xs text-slate-400">—</span>;
  const color = SENTIMENT_COLORS[sentiment] || "bg-slate-100 text-slate-700";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{sentiment}</span>;
}

const URGENCY_COLORS: Record<string, string> = {
  Low: "bg-slate-100 text-slate-700",
  Medium: "bg-amber-100 text-amber-800",
  High: "bg-rose-100 text-rose-800",
};

export function UrgencyBadge({ urgency }: { urgency: string | null | undefined }) {
  if (!urgency) return <span className="text-xs text-slate-400">—</span>;
  const color = URGENCY_COLORS[urgency] || "bg-slate-100 text-slate-700";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{urgency}</span>;
}

const RISK_COLORS: Record<string, string> = {
  Low: "bg-slate-100 text-slate-700",
  Medium: "bg-amber-100 text-amber-800",
  High: "bg-rose-100 text-rose-800",
};

export function RiskBadge({ level }: { level: string | null | undefined }) {
  if (!level) return <span className="text-xs text-slate-400">—</span>;
  const color = RISK_COLORS[level] || "bg-slate-100 text-slate-700";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{level}</span>;
}

const TREND_STYLES: Record<string, { color: string; icon: typeof Sparkles }> = {
  new: { color: "bg-brand-100 text-brand-700", icon: Sparkles },
  growing: { color: "bg-amber-100 text-amber-800", icon: TrendingUp },
  stable: { color: "bg-slate-100 text-slate-700", icon: Minus },
  declining: { color: "bg-emerald-100 text-emerald-800", icon: TrendingDown },
  all_time: { color: "bg-slate-100 text-slate-700", icon: Minus },
};

const TREND_LABELS: Record<string, string> = { all_time: "All-time" };

export function TrendBadge({ trend }: { trend: string | null | undefined }) {
  if (!trend) return <span className="text-xs text-slate-400">—</span>;
  const style = TREND_STYLES[trend] || { color: "bg-slate-100 text-slate-700", icon: Minus };
  const Icon = style.icon;
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium capitalize ${style.color}`}>
      <Icon className="h-3 w-3" />
      {TREND_LABELS[trend] || trend}
    </span>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-600">{pct}%</span>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const isDryRun = status === "dry_run";
  const isLive = status === "llm";
  const color = isDryRun ? "bg-amber-100 text-amber-800" : isLive ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700";
  const label = isDryRun ? "Dry-run (not a real model)" : isLive ? "Live LLM" : "Deterministic";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{label}</span>;
}

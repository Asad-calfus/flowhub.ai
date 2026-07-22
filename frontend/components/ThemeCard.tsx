import Link from "next/link";
import type { ThemeOut } from "@/lib/types";
import { formatDate } from "@/lib/formatters";
import { TrendBadge } from "./Badges";

export function ThemeCard({ theme, maxCount }: { theme: ThemeOut; maxCount?: number }) {
  const barPct = maxCount ? Math.max(6, Math.round((theme.feedback_count / maxCount) * 100)) : null;

  return (
    <Link href={`/themes/${theme.id}`} className="card-interactive block">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">{theme.name}</h3>
        <TrendBadge trend={theme.trend_status} />
      </div>
      <p className="mt-1 text-xs text-slate-500">{theme.feedback_count} feedback records</p>
      {barPct !== null && (
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-brand-500" style={{ width: `${barPct}%` }} />
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-1">
        {theme.keywords.slice(0, 5).map((kw) => (
          <span key={kw} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {kw}
          </span>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-400">
        {formatDate(theme.first_seen)} – {formatDate(theme.last_seen)}
      </p>
    </Link>
  );
}

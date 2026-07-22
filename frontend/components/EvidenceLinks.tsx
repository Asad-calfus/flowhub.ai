import Link from "next/link";
import { Link2 } from "lucide-react";
import type { SupportingEvidence } from "@/lib/types";

const STRENGTH_STYLES: Record<SupportingEvidence["evidence_strength"], string> = {
  high: "text-emerald-600",
  medium: "text-amber-600",
  low: "text-slate-500",
};

export function EvidenceLinks({ evidence }: { evidence: SupportingEvidence }) {
  const hasAny =
    evidence.representative_feedback_ids.length > 0 ||
    evidence.related_context_ids.length > 0 ||
    evidence.related_theme_ids.length > 0;
  if (!hasAny) return null;

  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
      <span className={`flex items-center gap-1 font-medium ${STRENGTH_STYLES[evidence.evidence_strength]}`}>
        <Link2 className="h-3 w-3" /> Evidence ({evidence.evidence_strength}):
      </span>
      {evidence.representative_feedback_ids.map((id) => (
        <Link key={id} href={`/feedback/${id}`} className="rounded-full bg-slate-100 px-2 py-0.5 text-brand-600 hover:bg-slate-200 hover:underline">
          {id}
        </Link>
      ))}
      {evidence.related_theme_ids.map((id) => (
        <Link key={id} href={`/themes/${id}`} className="rounded-full bg-slate-100 px-2 py-0.5 text-brand-600 hover:bg-slate-200 hover:underline">
          {id}
        </Link>
      ))}
      {evidence.related_context_ids.map((id) => (
        <span key={id} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-500">
          {id}
        </span>
      ))}
    </div>
  );
}

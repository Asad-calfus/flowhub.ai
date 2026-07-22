import Link from "next/link";
import type { AnalysisOut, FeedbackOut } from "@/lib/types";
import { truncate } from "@/lib/formatters";
import { SentimentBadge, UrgencyBadge } from "./Badges";

interface FeedbackTableProps {
  items: FeedbackOut[];
  analysisById: Record<string, AnalysisOut | null>;
}

export function FeedbackTable({ items, analysisById }: FeedbackTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="table-base">
        <thead>
          <tr>
            <th className="rounded-l-md">Feedback</th>
            <th>Source</th>
            <th>Tier</th>
            <th>Version</th>
            <th>Category</th>
            <th>Module</th>
            <th>Sentiment</th>
            <th>Urgency</th>
            <th className="rounded-r-md">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const analysis = analysisById[item.id];
            return (
              <tr key={item.id} className="transition-colors hover:bg-slate-50">
                <td className="max-w-md">
                  <Link href={`/feedback/${item.id}`} className="font-medium text-brand-600 hover:text-brand-700 hover:underline">
                    {truncate(item.feedback_text, 80)}
                  </Link>
                </td>
                <td className="text-slate-600">{item.source || "—"}</td>
                <td className="text-slate-600">{item.customer_tier || "—"}</td>
                <td className="text-slate-600">{item.product_version || "—"}</td>
                <td className="text-slate-600">{analysis?.category || "—"}</td>
                <td className="text-slate-600">{analysis?.product_module || "—"}</td>
                <td>
                  <SentimentBadge sentiment={analysis?.sentiment} />
                </td>
                <td>
                  <UrgencyBadge urgency={analysis?.urgency} />
                </td>
                <td className="capitalize text-slate-500">{item.processing_status.replace(/_/g, " ")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

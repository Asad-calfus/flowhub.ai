"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { Check, Gauge, MessageSquareText } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, SkeletonBlock } from "@/components/States";
import { RiskBadge, SentimentBadge } from "@/components/Badges";
import { MetricCard } from "@/components/MetricCard";
import { Pagination } from "@/components/Pagination";
import { formatDate, truncate } from "@/lib/formatters";

const PAGE_SIZE = 10;

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [page, setPage] = useState(1);
  const [reviewing, setReviewing] = useState(false);

  const risk = useApi(() => api.getCustomerRisk(id), [id]);
  const feedback = useApi(() => api.listFeedback({ customer_id: id, page, page_size: PAGE_SIZE }), [id, page]);

  const loading = risk.loading || feedback.loading;
  const error = risk.error || feedback.error;

  const handleReview = async () => {
    setReviewing(true);
    try {
      await api.markCustomerReviewed(id);
      risk.retry();
    } finally {
      setReviewing(false);
    }
  };

  return (
    <div>
      <PageHeader title={`Customer ${id}`} description="Churn risk, suggested action, and every feedback record from this customer in one place." />
      <div className="mx-auto max-w-5xl space-y-5 p-6">
        {error && (
          <ErrorState
            message={error}
            onRetry={() => {
              risk.retry();
              feedback.retry();
            }}
          />
        )}
        {loading && !error && <SkeletonBlock rows={8} />}

        {!loading && !error && risk.data && (
          <>
            <section className="card">
              <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Gauge className="h-3.5 w-3.5" /> Churn risk
              </h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <MetricCard label="Risk score" value={risk.data.risk_score} tone="rose" />
                <div>
                  <p className="text-xs text-slate-400">Risk level</p>
                  <div className="mt-1.5">
                    <RiskBadge level={risk.data.risk_level} />
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Tier</p>
                  <p className="mt-1 text-sm text-slate-700">{risk.data.customer_tier || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Last sentiment</p>
                  <div className="mt-1.5">
                    <SentimentBadge sentiment={risk.data.last_feedback_sentiment} />
                  </div>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
                <div>
                  <p className="text-xs text-slate-400">Suggested action</p>
                  <p className="text-sm font-medium text-slate-800">{risk.data.suggested_action}</p>
                </div>
                {risk.data.reviewed ? (
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-emerald-600">
                    <Check className="h-4 w-4" /> Reviewed
                  </span>
                ) : (
                  <button type="button" onClick={handleReview} disabled={reviewing} className="btn-secondary">
                    {reviewing ? "Saving…" : "Mark reviewed"}
                  </button>
                )}
              </div>
            </section>

            <section className="card">
              <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <MessageSquareText className="h-3.5 w-3.5" /> Feedback history
              </h2>
              {feedback.data && feedback.data.items.length > 0 ? (
                <>
                  <ul className="divide-y divide-slate-100">
                    {feedback.data.items.map((f) => (
                      <li key={f.id} className="flex items-center justify-between gap-3 py-2.5">
                        <Link href={`/feedback/${f.id}`} className="text-sm font-medium text-brand-600 hover:underline">
                          {truncate(f.feedback_text, 100)}
                        </Link>
                        <span className="whitespace-nowrap text-xs text-slate-400">{formatDate(f.feedback_created_at)}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4">
                    <Pagination page={feedback.data.page} pageSize={feedback.data.page_size} total={feedback.data.total} onPageChange={setPage} />
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-500">No feedback found for this customer.</p>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

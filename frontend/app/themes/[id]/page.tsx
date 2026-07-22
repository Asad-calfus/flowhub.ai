"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import Link from "next/link";
import { CalendarDays, Hash, MessageSquareText } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, SkeletonBlock } from "@/components/States";
import { TrendBadge } from "@/components/Badges";
import { SentimentChart } from "@/components/charts/SentimentChart";
import { Pagination } from "@/components/Pagination";
import { formatDate, truncate } from "@/lib/formatters";

const PAGE_SIZE = 10;

export default function ThemeDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [page, setPage] = useState(1);

  const theme = useApi(() => api.getTheme(id), [id]);
  const feedback = useApi(() => api.getThemeFeedback(id, page, PAGE_SIZE), [id, page]);

  const loading = theme.loading || feedback.loading;
  const error = theme.error || feedback.error;

  return (
    <div>
      <PageHeader title={theme.data?.name || "Theme"} description="Deterministic clustering output: keywords, trend, and representative feedback." />
      <div className="mx-auto max-w-6xl space-y-5 p-6">
        {error && (
          <ErrorState
            message={error}
            onRetry={() => {
              theme.retry();
              feedback.retry();
            }}
          />
        )}
        {loading && !error && <SkeletonBlock rows={8} />}

        {!loading && !error && theme.data && (
          <>
            <section className="card grid grid-cols-2 gap-5 sm:grid-cols-4">
              <div>
                <p className="flex items-center gap-1 text-xs text-slate-400">
                  <Hash className="h-3 w-3" /> Feedback count
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{theme.data.feedback_count}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Trend</p>
                <div className="mt-1.5">
                  <TrendBadge trend={theme.data.trend_status} />
                </div>
              </div>
              <div>
                <p className="flex items-center gap-1 text-xs text-slate-400">
                  <CalendarDays className="h-3 w-3" /> First seen
                </p>
                <p className="mt-1 text-sm text-slate-700">{formatDate(theme.data.first_seen)}</p>
              </div>
              <div>
                <p className="flex items-center gap-1 text-xs text-slate-400">
                  <CalendarDays className="h-3 w-3" /> Last seen
                </p>
                <p className="mt-1 text-sm text-slate-700">{formatDate(theme.data.last_seen)}</p>
              </div>
              <div className="col-span-2 border-t border-slate-100 pt-4 sm:col-span-4">
                <p className="mb-1.5 text-xs text-slate-400">Keywords</p>
                <div className="flex flex-wrap gap-1.5">
                  {theme.data.keywords.map((kw) => (
                    <span key={kw} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            </section>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <section className="card">
                <h2 className="mb-2 text-sm font-semibold text-slate-700">Sentiment distribution</h2>
                <SentimentChart distribution={theme.data.sentiment_distribution} />
              </section>
              <section className="card">
                <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-700">
                  <MessageSquareText className="h-4 w-4 text-slate-400" /> Representative feedback
                </h2>
                <ul className="space-y-3 divide-y divide-slate-100">
                  {theme.data.representative_feedback.map((rep) => (
                    <li key={String(rep.feedback_id)} className="pt-3 first:pt-0">
                      <Link href={`/feedback/${rep.feedback_id}`} className="text-sm font-medium text-brand-600 hover:underline">
                        {String(rep.feedback_id)}
                      </Link>
                      <p className="mt-0.5 text-sm text-slate-600">{truncate(String(rep.feedback_text || ""), 160)}</p>
                    </li>
                  ))}
                </ul>
              </section>
            </div>

            <section className="card">
              <h2 className="mb-3 text-sm font-semibold text-slate-700">Feedback in this theme</h2>
              {feedback.data && feedback.data.items.length > 0 ? (
                <>
                  <ul className="divide-y divide-slate-100">
                    {feedback.data.items.map((f) => (
                      <li key={f.id} className="py-2.5">
                        <Link href={`/feedback/${f.id}`} className="text-sm font-medium text-brand-600 hover:underline">
                          {truncate(f.feedback_text, 100)}
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4">
                    <Pagination page={feedback.data.page} pageSize={feedback.data.page_size} total={feedback.data.total} onPageChange={setPage} />
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-500">No feedback records found for this theme.</p>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

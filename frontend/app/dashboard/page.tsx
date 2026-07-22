"use client";

import Link from "next/link";
import { BarChart3, Gauge, Inbox, TriangleAlert } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { ErrorState, EmptyState, SkeletonBlock } from "@/components/States";
import { SentimentChart } from "@/components/charts/SentimentChart";
import { DistributionBarChart } from "@/components/charts/DistributionBarChart";
import { TrendBadge } from "@/components/Badges";
import { formatDate, formatPercent } from "@/lib/formatters";
import type { ContextInsight, ThemeInsight } from "@/lib/types";

function InsightList({ items, emptyLabel }: { items: (ThemeInsight | ContextInsight)[]; emptyLabel: string }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">{emptyLabel}</p>;
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={"theme_id" in item ? item.theme_id : item.context_id} className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 last:border-0">
          <div>
            <p className="text-sm font-medium text-slate-800">{item.title}</p>
            <p className="text-xs text-slate-500">{item.feedback_count} feedback</p>
          </div>
          <TrendBadge trend={item.trend} />
        </li>
      ))}
    </ul>
  );
}

export default function DashboardPage() {
  const feedbackTotal = useApi(() => api.listFeedback({ page: 1, page_size: 1 }), []);
  const latestReport = useApi(() => api.listReports(1, 1), []);

  const report = latestReport.data?.items[0];
  const reportDetail = useApi(() => (report ? api.getReport(report.id) : Promise.resolve(null)), [report?.id]);

  const loading = feedbackTotal.loading || latestReport.loading || reportDetail.loading;
  const error = feedbackTotal.error || latestReport.error || reportDetail.error;

  const metrics = reportDetail.data?.report.summary_metrics;

  return (
    <div>
      <PageHeader title="Dashboard" description="Feedback intelligence at a glance, built from stored classification, retrieval, and theme results." />
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        {error && (
          <ErrorState
            message={error}
            onRetry={() => {
              feedbackTotal.retry();
              latestReport.retry();
              reportDetail.retry();
            }}
          />
        )}

        {loading && !error && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonBlock key={i} rows={2} />
            ))}
          </div>
        )}

        {!loading && !error && (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <MetricCard label="Total feedback" value={feedbackTotal.data?.total ?? 0} hint="All time, from /feedback" icon={Inbox} tone="brand" />
              <MetricCard
                label="Feedback in latest report"
                value={metrics?.total_feedback ?? "—"}
                hint={report ? `${formatDate(report.start_date)} – ${formatDate(report.end_date)}` : "No report yet"}
                icon={BarChart3}
                tone="slate"
              />
              <MetricCard label="New / untracked issues" value={metrics?.new_issue_count ?? "—"} icon={TriangleAlert} tone="amber" />
              <MetricCard
                label="Avg. classification confidence"
                value={metrics?.average_confidence != null ? formatPercent(metrics.average_confidence) : "—"}
                icon={Gauge}
                tone="emerald"
              />
            </div>

            {!report && (
              <EmptyState
                title="No weekly report has been generated yet"
                description="Sentiment, category, and module breakdowns below are computed from the most recent weekly report. Generate one to populate this dashboard."
                action={
                  <Link href="/reports" className="btn-primary">
                    Go to Weekly Reports
                  </Link>
                }
              />
            )}

            {report && metrics && (
              <>
                <p className="text-xs text-slate-500">
                  Distributions below are computed by the backend for report {report.id} ({formatDate(report.start_date)} –{" "}
                  {formatDate(report.end_date)}), not recalculated in the frontend.
                </p>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Sentiment distribution</h2>
                    <SentimentChart distribution={metrics.sentiment_distribution} />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Feedback by type</h2>
                    <DistributionBarChart data={metrics.feedback_by_type} color="#4f46e5" />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Feedback by product module</h2>
                    <DistributionBarChart data={metrics.feedback_by_product_module} color="#0ca678" layout="vertical" />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Top themes by volume</h2>
                    <DistributionBarChart
                      data={Object.fromEntries(reportDetail.data!.report.top_pain_points.map((t) => [t.title, t.feedback_count]))}
                      color="#8b5cf6"
                      layout="vertical"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Top themes</h2>
                    <InsightList items={reportDetail.data!.report.top_pain_points} emptyLabel="No themes in this period." />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Growing themes</h2>
                    <InsightList items={reportDetail.data!.report.growing_themes} emptyLabel="No growing themes in this period." />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Known bug matches</h2>
                    <InsightList items={reportDetail.data!.report.known_bugs_growing} emptyLabel="No known-bug matches in this period." />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Feature request matches</h2>
                    <InsightList items={reportDetail.data!.report.feature_requests} emptyLabel="No feature-request matches in this period." />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">New / untracked issues</h2>
                    <InsightList items={reportDetail.data!.report.new_untracked_issues} emptyLabel="No new untracked issues in this period." />
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

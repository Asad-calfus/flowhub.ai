"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Download, FileCode2, Gauge, Inbox, LayoutList, Share2, TriangleAlert } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, SkeletonBlock } from "@/components/States";
import { StatusPill, TrendBadge, UrgencyBadge } from "@/components/Badges";
import { EvidenceLinks } from "@/components/EvidenceLinks";
import { MetricCard } from "@/components/MetricCard";
import { SentimentChart } from "@/components/charts/SentimentChart";
import { DistributionBarChart } from "@/components/charts/DistributionBarChart";
import { formatDate, formatDateTime, formatPercent } from "@/lib/formatters";
import type { ContextInsight, ThemeInsight } from "@/lib/types";

function ThemeInsightList({ items }: { items: ThemeInsight[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">None in this period.</p>;
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.theme_id} className="border-b border-slate-100 pb-2 last:border-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium text-slate-800">{item.title}</p>
            <TrendBadge trend={item.trend} />
          </div>
          <p className="text-sm text-slate-600">{item.description}</p>
          <EvidenceLinks evidence={item.evidence} />
        </li>
      ))}
    </ul>
  );
}

function ContextInsightList({ items }: { items: ContextInsight[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">None in this period.</p>;
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.context_id} className="border-b border-slate-100 pb-2 last:border-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium text-slate-800">{item.title}</p>
            <TrendBadge trend={item.trend} />
          </div>
          <p className="text-sm text-slate-600">{item.description}</p>
          <EvidenceLinks evidence={item.evidence} />
        </li>
      ))}
    </ul>
  );
}

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data, loading, error, retry } = useApi(() => api.getReport(id), [id]);
  const [showMarkdown, setShowMarkdown] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  const report = data?.report;

  const handleDownloadPdf = async () => {
    setPdfError(null);
    try {
      const blob = await api.downloadReportPdf(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setPdfError(err instanceof ApiError ? err.message : "Failed to download PDF.");
    }
  };

  const handleCopyShareLink = async () => {
    setShareStatus(null);
    try {
      const link = await api.createReportShareLink(id);
      const fullUrl = `${window.location.origin}${link.path}`;
      await navigator.clipboard.writeText(fullUrl);
      setShareStatus("Link copied (valid 7 days)");
    } catch (err) {
      setShareStatus(err instanceof ApiError ? err.message : "Failed to create share link.");
    }
  };

  return (
    <div>
      <PageHeader
        title={data ? `Report ${data.id}` : "Report"}
        description={
          report
            ? report.period.is_all_time
              ? `All-time (as of ${formatDate(report.period.end_date)})`
              : `${formatDate(report.period.start_date)} – ${formatDate(report.period.end_date)}`
            : undefined
        }
        action={
          data && (
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={handleDownloadPdf} className="btn-secondary">
                <Download className="h-4 w-4" /> Download PDF
              </button>
              <button onClick={handleCopyShareLink} className="btn-secondary">
                <Share2 className="h-4 w-4" /> Share link
              </button>
              <button onClick={() => setShowMarkdown((v) => !v)} className="btn-secondary">
                {showMarkdown ? (
                  <>
                    <LayoutList className="h-4 w-4" /> Structured view
                  </>
                ) : (
                  <>
                    <FileCode2 className="h-4 w-4" /> Markdown
                  </>
                )}
              </button>
            </div>
          )
        }
      />
      {(pdfError || shareStatus) && (
        <div className="mx-auto max-w-6xl px-6 pt-4 text-sm">
          {pdfError && <p className="text-rose-600">{pdfError}</p>}
          {shareStatus && <p className="text-slate-600">{shareStatus}</p>}
        </div>
      )}
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        {error && <ErrorState message={error} onRetry={retry} />}
        {loading && !error && <SkeletonBlock rows={10} />}

        {!loading && !error && data && report && (
          <>
            <section className="card flex flex-wrap items-center gap-x-6 gap-y-2">
              <StatusPill status={data.generation_method} />
              <span className="text-sm text-slate-600">Model: {data.model_name || "n/a"}</span>
              <span className="text-sm text-slate-600">Created {formatDateTime(data.created_at)}</span>
              <span className="text-sm text-slate-600">Module filter: {data.product_module_filter || "All"}</span>
              <span className="text-sm text-slate-600">Tier filter: {data.customer_tier_filter || "All"}</span>
            </section>

            {showMarkdown ? (
              <section className="card markdown-body">
                <ReactMarkdown>{data.markdown}</ReactMarkdown>
              </section>
            ) : (
              <>
                <section className="card">
                  <h2 className="mb-2 text-sm font-semibold text-slate-700">Executive summary</h2>
                  <p className="text-sm leading-relaxed text-slate-700">{report.executive_summary}</p>
                </section>

                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <MetricCard label="Total feedback" value={report.summary_metrics.total_feedback} icon={Inbox} tone="brand" />
                  <MetricCard label="New / untracked issues" value={report.summary_metrics.new_issue_count} icon={TriangleAlert} tone="amber" />
                  <MetricCard label="Low-confidence classifications" value={report.summary_metrics.low_confidence_count} icon={TriangleAlert} tone="rose" />
                  <MetricCard
                    label="Avg. confidence"
                    value={report.summary_metrics.average_confidence != null ? formatPercent(report.summary_metrics.average_confidence) : "—"}
                    icon={Gauge}
                    tone="emerald"
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Sentiment distribution</h2>
                    <SentimentChart distribution={report.summary_metrics.sentiment_distribution} />
                  </div>
                  <div className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Feedback by product module</h2>
                    <DistributionBarChart data={report.summary_metrics.feedback_by_product_module} color="#0ca678" layout="vertical" />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <section className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Top pain points</h2>
                    <ThemeInsightList items={report.top_pain_points} />
                  </section>
                  <section className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Growing themes</h2>
                    <ThemeInsightList items={report.growing_themes} />
                  </section>
                  <section className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Known bugs (growing)</h2>
                    <ContextInsightList items={report.known_bugs_growing} />
                  </section>
                  <section className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Feature requests</h2>
                    <ContextInsightList items={report.feature_requests} />
                  </section>
                  <section className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">Release-related issues</h2>
                    <ContextInsightList items={report.release_related_issues} />
                  </section>
                  <section className="card">
                    <h2 className="mb-2 text-sm font-semibold text-slate-700">New / untracked issues</h2>
                    <ContextInsightList items={report.new_untracked_issues} />
                  </section>
                </div>

                <section className="card">
                  <h2 className="mb-2 text-sm font-semibold text-slate-700">Recommended actions</h2>
                  {report.recommended_actions.length === 0 ? (
                    <p className="text-sm text-slate-400">No actions crossed the recommendation thresholds this period.</p>
                  ) : (
                    <ul className="space-y-2">
                      {report.recommended_actions.map((a) => (
                        <li key={a.action_id} className="border-b border-slate-100 pb-2 last:border-0">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium text-slate-800">{a.title}</p>
                            <UrgencyBadge urgency={a.priority} />
                          </div>
                          <p className="text-sm text-slate-600">{a.description}</p>
                          <EvidenceLinks evidence={a.evidence} />
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                {report.data_limitations.notes.length > 0 && (
                  <section className="card border-amber-200 bg-amber-50">
                    <h2 className="mb-2 text-sm font-semibold text-amber-800">Data limitations</h2>
                    <ul className="list-inside list-disc space-y-1 text-sm text-amber-800">
                      {report.data_limitations.notes.map((note, i) => (
                        <li key={i}>{note}</li>
                      ))}
                    </ul>
                  </section>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

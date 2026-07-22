"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import type { LucideIcon } from "lucide-react";
import { FileText, Link2, Sparkles, Tags, SearchCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, SkeletonBlock } from "@/components/States";
import { ConfidenceBar, SentimentBadge, UrgencyBadge } from "@/components/Badges";
import { formatConfidence, formatDate, formatDateTime } from "@/lib/formatters";
import type { AnalysisOut, ThemeOut } from "@/lib/types";

function SectionTitle({ icon: Icon, children }: { icon: LucideIcon; children: React.ReactNode }) {
  return (
    <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
      <Icon className="h-3.5 w-3.5" />
      {children}
    </h2>
  );
}

async function loadDetail(id: string) {
  const [feedback, similar, contextMatches] = await Promise.all([
    api.getFeedback(id),
    api.getSimilarFeedback(id).catch(() => []),
    api.getContextMatches(id).catch(() => null),
  ]);

  let analysis: AnalysisOut | null = null;
  try {
    analysis = await api.getAnalysis(id);
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 404) throw err;
  }

  // No single-feedback "which theme is this in" endpoint exists yet, so we
  // cross-reference the (small) themes list - see PROJECT_CONTEXT.md notes.
  let theme: ThemeOut | null = null;
  try {
    const themes = await api.listThemes(1, 100);
    const details = await Promise.all(themes.items.map((t) => api.getTheme(t.id).catch(() => null)));
    const match = details.find((d) => d?.members.some((m) => m.feedback_id === id));
    theme = match ?? null;
  } catch {
    theme = null;
  }

  return { feedback, similar, contextMatches, analysis, theme };
}

export default function FeedbackDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const fetcher = useCallback(() => loadDetail(id), [id]);
  const { data, loading, error, retry } = useApi(fetcher, [id]);

  return (
    <div>
      <PageHeader title={`Feedback ${id}`} description="Original customer data, AI-generated analysis, and retrieved supporting evidence, kept separate." />
      <div className="mx-auto max-w-5xl space-y-5 p-6">
        {error && <ErrorState message={error} onRetry={retry} />}
        {loading && !error && <SkeletonBlock rows={10} />}

        {!loading && !error && data && (
          <>
            <section className="card">
              <SectionTitle icon={FileText}>Original customer data</SectionTitle>
              <p className="whitespace-pre-wrap text-base text-slate-900">{data.feedback.feedback_text}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-600 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-slate-400">Source</p>
                  {data.feedback.source || "—"}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Customer tier</p>
                  {data.feedback.customer_tier || "—"}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Product version</p>
                  {data.feedback.product_version || "—"}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Rating</p>
                  {data.feedback.rating ?? "—"}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Language</p>
                  {data.feedback.language || "—"}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Submitted</p>
                  {formatDate(data.feedback.feedback_created_at)}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Processing status</p>
                  <span className="capitalize">{data.feedback.processing_status.replace(/_/g, " ")}</span>
                </div>
              </div>
            </section>

            <section className="card">
              <SectionTitle icon={Sparkles}>AI-generated analysis</SectionTitle>
              {!data.analysis ? (
                <p className="text-sm text-slate-500">Not yet classified. Run analysis via the API to populate this section.</p>
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                  <div>
                    <p className="text-xs text-slate-400">Feedback type</p>
                    {data.analysis.feedback_type}
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Category</p>
                    {data.analysis.category}
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Product module</p>
                    {data.analysis.product_module}
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Sentiment</p>
                    <SentimentBadge sentiment={data.analysis.sentiment} />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Urgency</p>
                    <UrgencyBadge urgency={data.analysis.urgency} />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Confidence</p>
                    <ConfidenceBar value={data.analysis.confidence} />
                  </div>
                  <div className="col-span-2 sm:col-span-3">
                    <p className="text-xs text-slate-400">Reasoning</p>
                    <p className="text-sm text-slate-700">{data.analysis.reasoning}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Model</p>
                    {data.analysis.model_name}
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Classified at</p>
                    {formatDateTime(data.analysis.created_at)}
                  </div>
                </div>
              )}
            </section>

            <section className="card">
              <SectionTitle icon={Tags}>Theme assignment</SectionTitle>
              {data.theme ? (
                <Link href={`/themes/${data.theme.id}`} className="text-sm font-medium text-brand-600 hover:underline">
                  {data.theme.name} ({data.theme.feedback_count} feedback)
                </Link>
              ) : (
                <p className="text-sm text-slate-500">Not assigned to any theme (unclustered).</p>
              )}
            </section>

            <section className="card">
              <SectionTitle icon={SearchCheck}>Retrieved evidence — similar feedback</SectionTitle>
              {data.similar.length === 0 ? (
                <p className="text-sm text-slate-500">No similar feedback found.</p>
              ) : (
                <ul className="space-y-2">
                  {data.similar.map((s) => (
                    <li key={s.matched_feedback_id} className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 last:border-0">
                      <div>
                        <Link href={`/feedback/${s.matched_feedback_id}`} className="text-sm font-medium text-brand-600 hover:underline">
                          {s.matched_feedback_id}
                        </Link>
                        <p className="text-sm text-slate-600">{s.text_preview}</p>
                      </div>
                      <span className="whitespace-nowrap text-xs text-slate-400">rank {s.rank} · {formatConfidence(s.similarity_score)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="card">
              <SectionTitle icon={Link2}>Retrieved evidence — context matches</SectionTitle>
              {!data.contextMatches || data.contextMatches.candidates.length === 0 ? (
                <p className="text-sm text-slate-500">No confident context match found.</p>
              ) : (
                <>
                  <p className="mb-2 text-sm text-slate-600">
                    Status: <span className="font-medium capitalize">{data.contextMatches.status.replace(/_/g, " ")}</span>
                  </p>
                  <ul className="space-y-2">
                    {data.contextMatches.candidates.map((c) => (
                      <li key={c.context_record_id} className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-slate-800">{c.title}</p>
                          <p className="text-xs text-slate-500 capitalize">{c.context_type.replace(/_/g, " ")}</p>
                        </div>
                        <span className="whitespace-nowrap text-xs text-slate-400">rank {c.rank} · {formatConfidence(c.similarity_score)}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

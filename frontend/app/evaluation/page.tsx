"use client";

import type { LucideIcon } from "lucide-react";
import { BarChart3, Layers, SearchCheck, Sparkles } from "lucide-react";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, EmptyState, SkeletonBlock } from "@/components/States";
import { formatPercent, titleCase } from "@/lib/formatters";

function SectionHeading({ icon: Icon, children }: { icon: LucideIcon; children: React.ReactNode }) {
  return (
    <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
      <Icon className="h-3.5 w-3.5" />
      {children}
    </h2>
  );
}

interface EvaluationResponse {
  classification: {
    baseline: { accuracy_by_field: Record<string, number>; is_dry_run: boolean };
    llm: { accuracy_by_field: Record<string, number>; is_dry_run: boolean; model: string | null };
  } | null;
  retrieval: {
    context_matching: Record<string, number>;
    similar_feedback: { same_theme_precision_at_5: number; same_theme_recall_at_5: number };
  } | null;
  themes: {
    n_total_records: number;
    n_themes: number;
    n_assigned: number;
    n_unclustered: number;
    clustering_config: Record<string, unknown>;
  } | null;
  report: Record<string, unknown> | null;
}

async function fetchEvaluation(): Promise<EvaluationResponse> {
  const res = await fetch("/api/evaluation");
  if (!res.ok) throw new Error("Failed to load evaluation results.");
  return res.json();
}

function AccuracyTable({ title, accuracy, dryRun }: { title: string; accuracy: Record<string, number>; dryRun?: boolean }) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        {dryRun && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            Dry-run stub — not a real model result
          </span>
        )}
      </div>
      <table className="table-base">
        <thead>
          <tr>
            <th>Field</th>
            <th>Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(accuracy).map(([field, value]) => (
            <tr key={field}>
              <td>{titleCase(field)}</td>
              <td>{formatPercent(value, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function EvaluationPage() {
  const { data, loading, error, retry } = useApi(fetchEvaluation, []);

  return (
    <div>
      <PageHeader
        title="Evaluation"
        description="Results from each phase's evaluator, computed against the 30-record gold set. Read from stored result files, not recalculated here."
      />
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        {error && <ErrorState message={error} onRetry={retry} />}
        {loading && !error && <SkeletonBlock rows={10} />}

        {!loading && !error && data && (
          <>
            <section className="card">
              <SectionHeading icon={Sparkles}>Classification &amp; sentiment accuracy</SectionHeading>
              {!data.classification ? (
                <EmptyState title="No classification evaluation results found." />
              ) : (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <AccuracyTable title="Baseline (rule-based + VADER)" accuracy={data.classification.baseline.accuracy_by_field} />
                  <AccuracyTable
                    title={`LLM few-shot classifier${data.classification.llm.model ? ` (${data.classification.llm.model})` : ""}`}
                    accuracy={data.classification.llm.accuracy_by_field}
                    dryRun={data.classification.llm.is_dry_run}
                  />
                </div>
              )}
              <p className="mt-3 text-xs text-slate-500">
                LLM numbers are currently identical to baseline because no live API key has been used yet - see
                PROJECT_CONTEXT.md, Phase 2.
              </p>
            </section>

            <section className="card">
              <SectionHeading icon={SearchCheck}>Retrieval metrics</SectionHeading>
              {!data.retrieval ? (
                <EmptyState title="No retrieval evaluation results found." />
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {Object.entries(data.retrieval.context_matching).map(([key, value]) => (
                    <div key={key}>
                      <p className="text-xs text-slate-400">{titleCase(key)}</p>
                      <p className="text-sm font-medium">{typeof value === "number" ? value.toFixed(3) : String(value)}</p>
                    </div>
                  ))}
                  <div>
                    <p className="text-xs text-slate-400">Same-theme precision@5</p>
                    <p className="text-sm font-medium">{data.retrieval.similar_feedback.same_theme_precision_at_5.toFixed(3)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Same-theme recall@5</p>
                    <p className="text-sm font-medium">{data.retrieval.similar_feedback.same_theme_recall_at_5.toFixed(3)}</p>
                  </div>
                </div>
              )}
            </section>

            <section className="card">
              <SectionHeading icon={Layers}>Theme metrics</SectionHeading>
              {!data.themes ? (
                <EmptyState title="No theme evaluation results found." />
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div>
                    <p className="text-xs text-slate-400">Total records</p>
                    <p className="text-sm font-medium">{data.themes.n_total_records}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Themes found</p>
                    <p className="text-sm font-medium">{data.themes.n_themes}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Assigned</p>
                    <p className="text-sm font-medium">{data.themes.n_assigned}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Unclustered</p>
                    <p className="text-sm font-medium">{data.themes.n_unclustered}</p>
                  </div>
                </div>
              )}
            </section>

            <section className="card">
              <SectionHeading icon={BarChart3}>Report evaluation metrics</SectionHeading>
              {!data.report ? (
                <EmptyState title="No report evaluation results found." description="Generate and evaluate a weekly report on the backend to populate this section." />
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {Object.entries(data.report)
                    .filter(([, value]) => typeof value === "number" || typeof value === "boolean")
                    .map(([key, value]) => (
                      <div key={key}>
                        <p className="text-xs text-slate-400">{titleCase(key)}</p>
                        <p className="text-sm font-medium">{typeof value === "boolean" ? String(value) : (value as number).toFixed(2)}</p>
                      </div>
                    ))}
                </div>
              )}
              <p className="mt-3 text-xs text-slate-500">
                Deterministic-path metrics are expected to be near-perfect by construction; the real limitation is data
                coverage, not report logic - see PROJECT_CONTEXT.md, Phase 6.
              </p>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

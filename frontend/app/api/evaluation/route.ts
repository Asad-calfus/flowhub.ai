import { readFile } from "fs/promises";
import path from "path";
import { NextResponse } from "next/server";

// Reads pre-computed, existing evaluation artifacts from the backend's results/
// directory (see PROJECT_CONTEXT.md - each phase's evaluator writes these; nothing
// here recomputes a metric or duplicates backend logic). Local dev/demo only: this
// assumes the frontend and backend share a filesystem, same as the Phase 7 spec's
// "from result files or backend endpoints" allowance for this one page.
const RESULTS_DIR = process.env.BACKEND_RESULTS_DIR || "../backend/results";

async function readJson(relativePath: string): Promise<unknown> {
  try {
    const full = path.join(process.cwd(), RESULTS_DIR, relativePath);
    const raw = await readFile(full, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function fieldAccuracies(fields: Record<string, { accuracy: number }> | undefined) {
  if (!fields) return {};
  return Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, v.accuracy]));
}

export async function GET() {
  const [classification, retrieval, themes, reportEval, llmRunMeta] = await Promise.all([
    readJson("evaluation_metrics.json"),
    readJson("retrieval/retrieval_metrics.json"),
    readJson("themes/theme_metrics.json"),
    readJson("reports/report_evaluation.json"),
    readJson("llm_run_meta.json"),
  ]);

  const c = classification as { baseline?: { fields?: any }; llm?: { fields?: any; run_summary?: any } } | null;
  const r = retrieval as { context_matching?: any; similar_feedback?: any } | null;
  const t = themes as { n_total_records?: number; n_themes?: number; n_assigned?: number; n_unclustered?: number; clustering_config?: any } | null;

  return NextResponse.json({
    classification: c && {
      baseline: { accuracy_by_field: fieldAccuracies(c.baseline?.fields), is_dry_run: false },
      llm: {
        accuracy_by_field: fieldAccuracies(c.llm?.fields),
        is_dry_run: Boolean(c.llm?.run_summary?.dry_run ?? (llmRunMeta as any)?.dry_run ?? true),
        model: (llmRunMeta as any)?.model ?? null,
      },
    },
    retrieval: r && {
      context_matching: r.context_matching,
      similar_feedback: r.similar_feedback && {
        same_theme_precision_at_5: r.similar_feedback.same_theme_precision_at_5,
        same_theme_recall_at_5: r.similar_feedback.same_theme_recall_at_5,
      },
    },
    themes: t,
    report: reportEval,
  });
}

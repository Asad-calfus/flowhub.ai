"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BarChart3,
  FileText,
  FlaskConical,
  Gauge,
  Inbox,
  LayoutDashboard,
  Network,
  SearchCheck,
  Sparkles,
  Tags,
  TriangleAlert,
  UploadCloud,
  Wand2,
} from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { HealthBadge } from "@/components/HealthBadge";
import { MetricCard } from "@/components/MetricCard";
import { TrendBadge } from "@/components/Badges";
import { ErrorState, SkeletonBlock } from "@/components/States";
import { formatDate, formatPercent } from "@/lib/formatters";
import { chooseDemoWorkspace, DEMO_WORKSPACE_ID, getStoredWorkspaceId, startNewWorkspace } from "@/lib/workspace";

const PIPELINE_STEPS: { icon: LucideIcon; title: string; description: string }[] = [
  {
    icon: Wand2,
    title: "Classify",
    description: "Every piece of feedback is tagged with type, category, module, sentiment, and urgency.",
  },
  {
    icon: SearchCheck,
    title: "Match & retrieve",
    description: "Semantic search finds similar feedback and checks it against known bugs and feature requests.",
  },
  {
    icon: Network,
    title: "Cluster into themes",
    description: "Related feedback is grouped into recurring topics, with a new / growing / stable / declining trend.",
  },
  {
    icon: FileText,
    title: "Weekly report",
    description: "Stored data rolls up into a shareable report with evidence-backed recommendations.",
  },
];

const QUICK_LINKS: { href: string; icon: LucideIcon; title: string; description: string }[] = [
  {
    href: "/dashboard",
    icon: LayoutDashboard,
    title: "Dashboard",
    description: "Sentiment, category, and module distributions from the latest weekly report.",
  },
  {
    href: "/feedback",
    icon: Inbox,
    title: "Feedback Inbox",
    description: "Browse and filter raw feedback alongside its stored AI classification.",
  },
  {
    href: "/themes",
    icon: Tags,
    title: "Themes",
    description: "Recurring topics found by local clustering, with trend status over time.",
  },
  {
    href: "/reports",
    icon: FileText,
    title: "Weekly Reports",
    description: "Generate or browse deterministic, evidence-traceable weekly summaries.",
  },
  {
    href: "/evaluation",
    icon: BarChart3,
    title: "Evaluation",
    description: "Accuracy of every AI step, measured against the hand-labeled gold set.",
  },
];

function WorkspaceChooser() {
  const router = useRouter();
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-700 via-brand-600 to-accent-600 p-6">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center text-white">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
            <Sparkles className="h-3.5 w-3.5" /> AI feedback intelligence
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight">Welcome to FlowHub</h1>
          <p className="mt-2 text-sm text-brand-50">Bring your own feedback CSV, or explore with sample data first.</p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <button
            onClick={() => {
              startNewWorkspace();
              router.push("/get-started");
            }}
            className="card-interactive bg-white text-left"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <UploadCloud className="h-4 w-4" />
            </span>
            <h3 className="mt-3 text-sm font-semibold text-slate-900">Start your own workspace</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-500">
              Upload your own feedback CSV and get a private dashboard built from just your data.
            </p>
          </button>
          <button
            onClick={() => {
              chooseDemoWorkspace();
              window.location.reload();
            }}
            className="card-interactive bg-white/95 text-left"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
              <FlaskConical className="h-4 w-4" />
            </span>
            <h3 className="mt-3 text-sm font-semibold text-slate-900">View demo data</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-500">
              Explore the full experience with FlowHub's sample dataset - already classified and clustered.
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}

function EmptyWorkspacePrompt() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="card max-w-md text-center">
        <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-600">
          <UploadCloud className="h-5 w-5" />
        </span>
        <h2 className="mt-3 text-sm font-semibold text-slate-900">Your workspace is empty</h2>
        <p className="mt-1 text-sm text-slate-500">Upload a feedback CSV to build your dashboard.</p>
        <Link href="/get-started" className="btn-primary mt-4 inline-flex">
          Upload feedback <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [workspaceId, setWorkspaceId] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    setWorkspaceId(getStoredWorkspaceId());
  }, []);

  const hasWorkspace = workspaceId !== undefined && workspaceId !== null;
  const feedbackTotal = useApi(() => (hasWorkspace ? api.listFeedback({ page: 1, page_size: 1 }) : Promise.resolve(null)), [hasWorkspace]);
  const themesTotal = useApi(() => (hasWorkspace ? api.listThemes(1, 1) : Promise.resolve(null)), [hasWorkspace]);
  const latestReport = useApi(() => (hasWorkspace ? api.listReports(1, 1) : Promise.resolve(null)), [hasWorkspace]);
  const report = latestReport.data?.items[0];
  const reportDetail = useApi(() => (report ? api.getReport(report.id) : Promise.resolve(null)), [report?.id]);

  if (workspaceId === undefined) return null; // resolving localStorage, avoids a flash
  if (workspaceId === null) return <WorkspaceChooser />;

  const loading = feedbackTotal.loading || themesTotal.loading || latestReport.loading || reportDetail.loading;
  const error = feedbackTotal.error || themesTotal.error || latestReport.error || reportDetail.error;

  if (!loading && !error && workspaceId !== DEMO_WORKSPACE_ID && (feedbackTotal.data?.total ?? 0) === 0) {
    return <EmptyWorkspacePrompt />;
  }

  const metrics = reportDetail.data?.report.summary_metrics;
  const topTheme = reportDetail.data?.report.top_pain_points[0];
  const topIssue = reportDetail.data?.report.new_untracked_issues[0];

  return (
    <div className="pb-16">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-slate-200 bg-gradient-to-br from-brand-700 via-brand-600 to-accent-600 px-6 pb-14 pt-16 text-white sm:px-10 lg:pl-10">
        <div
          className="pointer-events-none absolute inset-0 opacity-20"
          style={{ backgroundImage: "radial-gradient(circle at 20% 20%, white 0, transparent 45%)" }}
          aria-hidden="true"
        />
        <div className="relative mx-auto max-w-4xl pl-10 lg:pl-0">
          <div className="mb-4 flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
              <Sparkles className="h-3.5 w-3.5" /> AI feedback intelligence
            </span>
            <div className="hidden sm:block">
              <HealthBadge />
            </div>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Turn every piece of FlowHub feedback into a decision.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-brand-50 sm:text-base">
            Classification, similarity search, theme clustering, and weekly reporting over your customer
            feedback — every number traced back to stored data, no black boxes.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 rounded-lg bg-white px-4 py-2 text-sm font-medium text-brand-700 shadow-sm transition-colors hover:bg-brand-50">
              Open dashboard <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/themes" className="inline-flex items-center gap-1.5 rounded-lg border border-white/30 bg-white/10 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/20">
              Browse themes
            </Link>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl space-y-10 px-6 pt-8 sm:px-10">
        {error && (
          <ErrorState
            message={error}
            onRetry={() => {
              feedbackTotal.retry();
              themesTotal.retry();
              latestReport.retry();
              reportDetail.retry();
            }}
          />
        )}

        {loading && !error && (
          <div className="-mt-16 grid grid-cols-2 gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonBlock key={i} rows={2} />
            ))}
          </div>
        )}

        {!loading && !error && (
          <>
            {/* KPI ribbon */}
            <div className="-mt-16 grid grid-cols-2 gap-4 md:grid-cols-4">
              <MetricCard label="Total feedback" value={feedbackTotal.data?.total ?? 0} hint="All time" icon={Inbox} tone="brand" />
              <MetricCard label="Active themes" value={themesTotal.data?.total ?? 0} hint="Found by clustering" icon={Tags} tone="slate" />
              <MetricCard label="New / untracked issues" value={metrics?.new_issue_count ?? "—"} hint={report ? "Latest report" : "No report yet"} icon={TriangleAlert} tone="amber" />
              <MetricCard
                label="Avg. classification confidence"
                value={metrics?.average_confidence != null ? formatPercent(metrics.average_confidence) : "—"}
                hint={report ? "Latest report" : "No report yet"}
                icon={Gauge}
                tone="emerald"
              />
            </div>

            {/* How it works */}
            <section>
              <h2 className="section-label mb-3">How it works</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {PIPELINE_STEPS.map((step, i) => (
                  <div key={step.title} className="card relative">
                    <span className="absolute right-4 top-4 text-2xl font-semibold text-slate-100">{i + 1}</span>
                    <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                      <step.icon className="h-4 w-4" />
                    </span>
                    <h3 className="text-sm font-semibold text-slate-900">{step.title}</h3>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">{step.description}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Latest report teaser */}
            <section>
              <h2 className="section-label mb-3">Latest weekly report</h2>
              {!report ? (
                <div className="card flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-800">No weekly report has been generated yet</p>
                    <p className="mt-1 text-xs text-slate-500">Generate one to see top themes and issues here.</p>
                  </div>
                  <Link href="/reports" className="btn-primary shrink-0">
                    Generate a report
                  </Link>
                </div>
              ) : (
                <div className="card">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <p className="text-sm font-medium text-slate-800">
                      {formatDate(report.start_date)} – {formatDate(report.end_date)}
                    </p>
                    <Link href={`/reports/${report.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline">
                      View full report <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                  <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-xs font-medium text-slate-500">Top theme</p>
                      {topTheme ? (
                        <div className="mt-1 flex items-center justify-between gap-2">
                          <p className="text-sm text-slate-800">{topTheme.title}</p>
                          <TrendBadge trend={topTheme.trend} />
                        </div>
                      ) : (
                        <p className="mt-1 text-sm text-slate-400">No themes in this period.</p>
                      )}
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-500">Top new / untracked issue</p>
                      {topIssue ? (
                        <div className="mt-1 flex items-center justify-between gap-2">
                          <p className="text-sm text-slate-800">{topIssue.title}</p>
                          <TrendBadge trend={topIssue.trend} />
                        </div>
                      ) : (
                        <p className="mt-1 text-sm text-slate-400">No new untracked issues in this period.</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>
          </>
        )}

        {/* Quick nav */}
        <section>
          <h2 className="section-label mb-3">Go to</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {QUICK_LINKS.map((link) => (
              <Link key={link.href} href={link.href} className="card-interactive block">
                <div className="flex items-start justify-between">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                    <link.icon className="h-4 w-4" />
                  </span>
                  <ArrowRight className="h-4 w-4 text-slate-300 transition-transform group-hover:translate-x-0.5" />
                </div>
                <h3 className="mt-3 text-sm font-semibold text-slate-900">{link.title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">{link.description}</p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

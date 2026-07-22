"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ReportGenerationForm } from "@/components/ReportGenerationForm";
import { ErrorState, EmptyState, SkeletonBlock } from "@/components/States";
import { StatusPill } from "@/components/Badges";
import { formatDate, formatDateTime } from "@/lib/formatters";

export default function ReportsPage() {
  const router = useRouter();
  const { data, loading, error, retry } = useApi(() => api.listReports(1, 50), []);

  return (
    <div>
      <PageHeader title="Weekly Reports" description="Deterministic, backend-computed weekly insight reports - every number traces back to stored data." />
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <ReportGenerationForm onGenerated={(report) => router.push(`/reports/${report.id}`)} />

        {error && <ErrorState message={error} onRetry={retry} />}
        {loading && !error && <SkeletonBlock rows={6} />}

        {!loading && !error && data && data.items.length === 0 && (
          <EmptyState title="No reports generated yet" description="Use the form above to generate the first weekly report." />
        )}

        {!loading && !error && data && data.items.length > 0 && (
          <div className="card overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Report</th>
                  <th>Period</th>
                  <th>Mode</th>
                  <th>Module filter</th>
                  <th>Tier filter</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50">
                    <td>
                      <Link href={`/reports/${r.id}`} className="font-medium text-brand-600 hover:underline">
                        {r.id}
                      </Link>
                    </td>
                    <td>{r.is_all_time ? "All-time" : `${formatDate(r.start_date)} – ${formatDate(r.end_date)}`}</td>
                    <td>
                      <StatusPill status={r.generation_method} />
                    </td>
                    <td>{r.product_module_filter || "All"}</td>
                    <td>{r.customer_tier_filter || "All"}</td>
                    <td>{formatDateTime(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { AlertTriangle, TrendingDown, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, EmptyState, SkeletonBlock } from "@/components/States";
import { MetricCard } from "@/components/MetricCard";
import { RiskBadge, SentimentBadge } from "@/components/Badges";
import { DistributionBarChart } from "@/components/charts/DistributionBarChart";

export default function ChurnPage() {
  const { data, loading, error, retry } = useApi(() => api.listAtRiskCustomers(50), []);

  const highRisk = data?.filter((c) => c.risk_level === "High").length ?? 0;
  const mediumRisk = data?.filter((c) => c.risk_level === "Medium").length ?? 0;
  const topChart = Object.fromEntries((data ?? []).slice(0, 10).map((c) => [c.customer_id, c.risk_score]));

  return (
    <div>
      <PageHeader
        title="Churn Risk"
        description="Rule-based risk score per customer - derived from negative-feedback ratio, high-urgency ratio, and recency of negative sentiment. No LLM, every number traces back to stored feedback."
      />
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        {error && <ErrorState message={error} onRetry={retry} />}
        {loading && !error && <SkeletonBlock rows={8} />}

        {!loading && !error && data && data.length === 0 && (
          <EmptyState title="No customer data yet" description="Risk scores appear once feedback records have a customer_id and have been classified." />
        )}

        {!loading && !error && data && data.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              <MetricCard label="Customers tracked" value={data.length} icon={Users} tone="brand" />
              <MetricCard label="High risk" value={highRisk} icon={AlertTriangle} tone="rose" />
              <MetricCard label="Medium risk" value={mediumRisk} icon={TrendingDown} tone="amber" />
            </div>

            <div className="card">
              <h2 className="mb-2 text-sm font-semibold text-slate-700">Top 10 at-risk customers</h2>
              <DistributionBarChart data={topChart} color="#e34948" layout="vertical" />
            </div>

            <div className="card overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Tier</th>
                    <th>Risk score</th>
                    <th>Risk level</th>
                    <th>Total feedback</th>
                    <th>Negative</th>
                    <th>High urgency</th>
                    <th>Last sentiment</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((c) => (
                    <tr key={c.customer_id} className="hover:bg-slate-50">
                      <td className="font-medium text-slate-800">{c.customer_id}</td>
                      <td className="text-slate-600">{c.customer_tier || "—"}</td>
                      <td className="text-slate-600">{c.risk_score}</td>
                      <td>
                        <RiskBadge level={c.risk_level} />
                      </td>
                      <td className="text-slate-600">{c.total_feedback}</td>
                      <td className="text-slate-600">{c.negative_count}</td>
                      <td className="text-slate-600">{c.high_urgency_count}</td>
                      <td>
                        <SentimentBadge sentiment={c.last_feedback_sentiment} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

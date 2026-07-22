"use client";

import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { FeedbackCsvImport } from "@/components/FeedbackCsvImport";
import { ClassifyPanel } from "@/components/ClassifyPanel";
import { RetrievalPanel } from "@/components/RetrievalPanel";
import { FeedbackFilters } from "@/components/FeedbackFilters";
import { FeedbackTable } from "@/components/FeedbackTable";
import { Pagination } from "@/components/Pagination";
import { ErrorState, EmptyState, SkeletonBlock } from "@/components/States";
import type { AnalysisOut, FeedbackListFilters } from "@/lib/types";

const PAGE_SIZE = 20;

async function loadPage(filters: FeedbackListFilters) {
  const page = await api.listFeedback({ ...filters, page: filters.page ?? 1, page_size: PAGE_SIZE });
  const analysisEntries = await Promise.all(
    page.items.map(async (item) => {
      try {
        const analysis = await api.getAnalysis(item.id);
        return [item.id, analysis] as [string, AnalysisOut];
      } catch {
        return [item.id, null] as [string, null];
      }
    })
  );
  return { page, analysisById: Object.fromEntries(analysisEntries) };
}

export default function FeedbackInboxPage() {
  const [filters, setFilters] = useState<FeedbackListFilters>({ page: 1 });
  const [refreshToken, setRefreshToken] = useState(0);
  const fetcher = useCallback(() => loadPage(filters), [filters]);
  const { data, loading, error, retry } = useApi(fetcher, [filters]);

  const refreshAll = () => {
    retry();
    setRefreshToken((t) => t + 1);
  };

  return (
    <div>
      <PageHeader title="Feedback Inbox" description="Browse raw customer feedback alongside its latest stored classification." />
      <div className="mx-auto max-w-7xl space-y-4 p-6">
        <FeedbackCsvImport onImported={refreshAll} />
        <ClassifyPanel key={refreshToken} onDone={refreshAll} />
        <RetrievalPanel onDone={refreshAll} />
        <FeedbackFilters filters={filters} onChange={setFilters} />

        {error && <ErrorState message={error} onRetry={retry} />}

        {loading && !error && <SkeletonBlock rows={8} />}

        {!loading && !error && data && data.page.items.length === 0 && (
          <EmptyState title="No feedback matches these filters" description="Try clearing a filter or check back after more data is imported." />
        )}

        {!loading && !error && data && data.page.items.length > 0 && (
          <div className="card">
            <FeedbackTable items={data.page.items} analysisById={data.analysisById} />
          </div>
        )}

        {!loading && !error && data && data.page.total > 0 && (
          <Pagination
            page={data.page.page}
            pageSize={data.page.page_size}
            total={data.page.total}
            onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
          />
        )}
      </div>
    </div>
  );
}

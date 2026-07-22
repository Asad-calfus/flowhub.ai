"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/PageHeader";
import { ThemeCard } from "@/components/ThemeCard";
import { ErrorState, EmptyState, SkeletonBlock } from "@/components/States";
import { Pagination } from "@/components/Pagination";

const PAGE_SIZE = 12;

export default function ThemesPage() {
  const [page, setPage] = useState(1);
  const { data, loading, error, retry } = useApi(() => api.listThemes(page, PAGE_SIZE), [page]);

  return (
    <div>
      <PageHeader title="Themes" description="Recurring topics found by local clustering over feedback embeddings - no LLM involved." />
      <div className="mx-auto max-w-7xl space-y-4 p-6">
        {error && <ErrorState message={error} onRetry={retry} />}
        {loading && !error && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonBlock key={i} rows={3} />
            ))}
          </div>
        )}

        {!loading && !error && data && data.items.length === 0 && (
          <EmptyState title="No themes found" description="Run theme clustering and import results to populate this page." />
        )}

        {!loading && !error && data && data.items.length > 0 && (
          <>
            <p className="text-sm text-slate-500">{data.total} theme{data.total === 1 ? "" : "s"} found</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((theme) => (
                <ThemeCard key={theme.id} theme={theme} maxCount={Math.max(...data.items.map((t) => t.feedback_count))} />
              ))}
            </div>
            <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}

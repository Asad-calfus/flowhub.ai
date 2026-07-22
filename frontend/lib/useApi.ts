"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

/** Fetches `fn()` whenever `deps` change. Exposes loading/error/retry for consistent UI states. */
export function useApi<T>(fn: () => Promise<T>, deps: unknown[]): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fn()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => load(), [load, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { data, loading, error, retry };
}

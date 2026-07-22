"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth } from "@/lib/api";

export function HealthBadge() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () => checkBackendHealth().then((ok) => !cancelled && setHealthy(ok));
    check();
    const interval = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const label = healthy === null ? "Checking…" : healthy ? "Backend connected" : "Backend unreachable";
  const dotColor = healthy === null ? "bg-slate-300" : healthy ? "bg-emerald-500" : "bg-rose-500";

  return (
    <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
      <span className={`relative flex h-2 w-2 ${dotColor} rounded-full`}>
        {healthy && <span className={`absolute inset-0 animate-ping rounded-full ${dotColor} opacity-75`} />}
      </span>
      {label}
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FlaskConical, LayoutGrid } from "lucide-react";
import { clearWorkspace, DEMO_WORKSPACE_ID, getStoredWorkspaceId } from "@/lib/workspace";

export function WorkspaceBadge() {
  const router = useRouter();
  const [workspaceId, setWorkspaceId] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    setWorkspaceId(getStoredWorkspaceId());
  }, []);

  if (workspaceId === undefined) return null; // avoid a hydration flash

  const isDemo = workspaceId === DEMO_WORKSPACE_ID || workspaceId === null;

  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs">
      <span className="flex items-center gap-1.5 font-medium text-slate-600">
        {isDemo ? <FlaskConical className="h-3.5 w-3.5" /> : <LayoutGrid className="h-3.5 w-3.5" />}
        {isDemo ? "Demo data" : "Your workspace"}
      </span>
      <button
        onClick={() => {
          clearWorkspace();
          router.push("/");
        }}
        className="font-medium text-brand-600 hover:underline"
      >
        Switch
      </button>
    </div>
  );
}

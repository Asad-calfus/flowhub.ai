import { Inbox, TriangleAlert } from "lucide-react";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="card flex items-start gap-3 border-rose-200 bg-rose-50 text-rose-800">
      <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0" />
      <div>
        <p className="text-sm font-medium">Something went wrong</p>
        <p className="mt-1 text-sm">{message}</p>
        {onRetry && (
          <button onClick={onRetry} className="mt-3 rounded-md bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-700">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="card flex flex-col items-center gap-1 py-10 text-center text-slate-500">
      <span className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
        <Inbox className="h-5 w-5" />
      </span>
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {description && <p className="max-w-md text-sm">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-200 ${className}`} />;
}

export function SkeletonBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div className="card space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} />
      ))}
    </div>
  );
}

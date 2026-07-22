import { HealthBadge } from "./HealthBadge";

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white/90 py-4 pl-16 pr-6 backdrop-blur lg:pl-6">
      <div className="min-w-0">
        <h1 className="page-heading truncate">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-slate-500">{description}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-4">
        {action}
        <HealthBadge />
      </div>
    </div>
  );
}

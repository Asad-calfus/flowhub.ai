"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Home,
  Inbox,
  LayoutDashboard,
  Menu,
  MessagesSquare,
  Sparkles,
  Tags,
  FileText,
  X,
} from "lucide-react";
import { WorkspaceBadge } from "./WorkspaceBadge";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/feedback", label: "Feedback Inbox", icon: Inbox },
  { href: "/themes", label: "Themes", icon: Tags },
  { href: "/reports", label: "Weekly Reports", icon: FileText },
  { href: "/churn", label: "Churn Risk", icon: AlertTriangle },
  { href: "/copilot", label: "AI Copilot", icon: Sparkles },
  { href: "/evaluation", label: "Evaluation", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open navigation"
        className="fixed left-4 top-4 z-30 flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-card lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/30 lg:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-full w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-5 py-5">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <MessagesSquare className="h-4 w-4" />
            </span>
            <span>
              <p className="text-sm font-semibold leading-tight text-slate-900">FlowHub</p>
              <p className="text-xs leading-tight text-slate-500">Feedback Intelligence</p>
            </span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
            className="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const active = item.exact ? pathname === item.href : pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-brand-600" />}
                <Icon className={`h-4 w-4 shrink-0 ${active ? "text-brand-600" : "text-slate-400 group-hover:text-slate-500"}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="space-y-2 border-t border-slate-200 p-3">
          <WorkspaceBadge />
          <p className="px-1 text-xs text-slate-400">FlowHub AI &middot; v1</p>
        </div>
      </aside>
    </>
  );
}

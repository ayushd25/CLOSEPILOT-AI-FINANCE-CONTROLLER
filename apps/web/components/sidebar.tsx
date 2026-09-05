"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileSearch,
  AlertTriangle,
  FlaskConical,
  Share2,
  History,
  Database,
  Landmark,
  SlidersHorizontal,
  BookOpen,
  TrendingUp,
  Receipt,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/explore", label: "Command Center", icon: LayoutDashboard },
  { href: "/reconciliation", label: "Reconciliation", icon: FileSearch },
  { href: "/exceptions", label: "Exceptions", icon: AlertTriangle },
  { href: "/forecast", label: "Cash Forecast", icon: TrendingUp },
  { href: "/tax", label: "Tax-Line Matcher", icon: Receipt },
  { href: "/evaluation", label: "Evaluation Lab", icon: FlaskConical },
  { href: "/evidence", label: "Evidence Graph", icon: Share2 },
  { href: "/audit", label: "Audit Trail", icon: History },
  { href: "/sources", label: "Data Sources", icon: Database },
  { href: "/policies", label: "Policies", icon: SlidersHorizontal },
  { href: "/docs", label: "Documentation", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-56 flex-col border-r border-white/5 bg-[#0A1626] text-slate-200">
      <div className="relative flex items-center gap-2.5 border-b border-white/5 p-4">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-[0_4px_16px_rgba(16,185,129,0.4)]">
          <Landmark className="h-4 w-4" size={18} />
        </div>
        <div>
          <p className="text-sm font-bold leading-none tracking-tight text-white">ClosePilot</p>
          <p className="mt-0.5 text-[10px] font-medium uppercase tracking-widest text-emerald-400/90">
            Finance Controller
          </p>
        </div>
        <div className="absolute inset-x-4 bottom-0 h-px bg-gradient-to-r from-transparent via-emerald-400/40 to-transparent" />
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "border-l-2 border-emerald-400 bg-emerald-400/10 text-emerald-300"
                  : "border-l-2 border-transparent text-slate-400 hover:bg-white/5 hover:text-white",
              )}
            >
              <Icon className={cn("h-4 w-4", active ? "text-emerald-400" : "text-slate-500 group-hover:text-slate-300")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/5 p-4">
        <div className="mb-3 flex items-center gap-1.5 text-[10px] font-medium text-slate-500">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
          Deterministic core · AI advisory
        </div>
        <p className="text-[10px] leading-relaxed text-slate-500">
          Models investigate.
          <br />
          Rules authorize.
          <br />
          Evidence proves.
        </p>
      </div>
    </aside>
  );
}

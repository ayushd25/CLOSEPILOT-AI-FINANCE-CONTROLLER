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
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Command Center", icon: LayoutDashboard },
  { href: "/reconciliation", label: "Reconciliation", icon: FileSearch },
  { href: "/exceptions", label: "Exceptions", icon: AlertTriangle },
  { href: "/evaluation", label: "Evaluation Lab", icon: FlaskConical },
  { href: "/evidence", label: "Evidence Graph", icon: Share2 },
  { href: "/audit", label: "Audit Trail", icon: History },
  { href: "/sources", label: "Data Sources", icon: Database },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-56 flex-col border-r bg-white">
      <div className="flex items-center gap-2 border-b p-4">
        <div className="flex h-8 w-8 items-center justify-center rounded bg-emerald-600 text-white">
          <Shield className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-bold leading-none">ClosePilot</p>
          <p className="text-[10px] text-muted-foreground">Finance Controller</p>
        </div>
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
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-emerald-50 text-emerald-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4">
        <p className="text-[10px] text-gray-400">
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

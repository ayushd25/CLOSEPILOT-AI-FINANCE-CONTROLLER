"use client";

import { Sidebar } from "@/components/sidebar";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-56 flex-1 p-8">{children}</main>
    </div>
  );
}

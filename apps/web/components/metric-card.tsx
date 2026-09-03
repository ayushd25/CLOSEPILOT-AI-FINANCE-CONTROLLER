"use client";

import { cn } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  sublabel,
  className,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border bg-white p-4", className)}>
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {sublabel && <p className="mt-1 text-xs text-gray-400">{sublabel}</p>}
    </div>
  );
}

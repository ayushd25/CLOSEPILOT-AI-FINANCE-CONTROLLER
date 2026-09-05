"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout";
import { MetricCard } from "@/components/metric-card";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw, TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";

interface Summary {
  total_records: number;
  total_cases: number;
  reconciled: number;
  auto_resolved: number;
  human_review: number;
  exceptions: number;
  unmatched: number;
  total_payments: number;
  total_settlements: number;
  total_bank_transactions: number;
  precision: number;
  recall: number;
  false_auto_match_rate: number;
}

interface Trends {
  reconciliation_runs: Array<{
    run_id: string;
    started_at: string;
    total_records: number;
    matched: number;
    exceptions: number;
    auto_resolved: number;
    duration_seconds: number;
  }>;
  risk_distribution: Record<string, number>;
  source_health: {
    synthetic: { records: number };
  };
}

export default function CommandCenter() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [trends, setTrends] = useState<Trends | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, t] = await Promise.all([api.get<Summary>("/dashboard/summary"), api.get<Trends>("/dashboard/trends")]);
      setSummary(s);
      setTrends(t);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Command Center</h1>
          <p className="text-sm text-gray-500">Live operational metrics from real backend data</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {loading && !summary ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-8">
            <MetricCard label="Total Records" value={summary?.total_records ?? 0} />
            <MetricCard label="Reconciled" value={summary?.reconciled ?? 0} />
            <MetricCard label="Auto-Resolved" value={summary?.auto_resolved ?? 0} />
            <MetricCard label="Exceptions" value={summary?.exceptions ?? 0} />
            <MetricCard label="Human Review" value={summary?.human_review ?? 0} />
            <MetricCard label="Precision" value={`${((summary?.precision ?? 0) * 100).toFixed(1)}%`} />
            <MetricCard label="Recall" value={`${((summary?.recall ?? 0) * 100).toFixed(1)}%`} />
            <MetricCard label="False Auto-Match" value={`${((summary?.false_auto_match_rate ?? 0) * 100).toFixed(1)}%`} />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-600" />
                  Reconciliation Runs
                </CardTitle>
                <CardDescription>Recent reconciliation activity</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(trends?.reconciliation_runs?.length ?? 0) === 0 && (
                    <p className="text-sm text-gray-400">No reconciliation runs yet. Run reconciliation to populate data.</p>
                  )}
                  {trends?.reconciliation_runs?.slice(0, 5).map((r) => (
                    <div key={r.run_id} className="flex items-center justify-between rounded-md border p-2">
                      <div>
                        <p className="text-sm font-medium">{r.total_records} records processed</p>
                        <p className="text-xs text-gray-400">
                          {r.matched} matched · {r.exceptions} exceptions · {r.auto_resolved} auto-resolved
                        </p>
                      </div>
                      <span className="text-xs text-gray-400">{r.duration_seconds?.toFixed(1)}s</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  Risk Distribution
                </CardTitle>
                <CardDescription>Cases by risk level</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(trends?.risk_distribution ?? {}).map(([risk, count]) => (
                    <div key={risk} className="flex items-center justify-between">
                      <Badge
                        variant={
                          risk === "LOW" ? "success" : risk === "MEDIUM" ? "warning" : "destructive"
                        }
                      >
                        {risk}
                      </Badge>
                      <span className="text-sm font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  Source Health
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="rounded-md border p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold">Synthetic</p>
                      <Badge variant="success">Active</Badge>
                    </div>
                    <p className="mt-2 text-xs text-gray-500">
                      {trends?.source_health?.synthetic?.records ?? 0} records available
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
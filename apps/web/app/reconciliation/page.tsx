"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { RefreshCw, Play, ArrowRight } from "lucide-react";

interface CaseItem {
  case_id: string;
  status: string;
  risk: string;
  match_score: number;
  outcome_type: string;
  amount: number;
  currency: string;
  related_record_ids: string[];
  source: string;
}

interface CasesResponse {
  total: number;
  cases: CaseItem[];
}

export default function Reconciliation() {
  const [data, setData] = useState<CasesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runner, setRunner] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [riskFilter, setRiskFilter] = useState<string>("");

  const fetchCases = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (riskFilter) params.set("risk", riskFilter);
      const res = await api.get<CasesResponse>(`/reconciliation/cases?${params.toString()}&limit=100`);
      setData(res);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchCases();
  }, [statusFilter, riskFilter]);

  const runReconciliation = async () => {
    setRunning(true);
    try {
      const res = await api.post<any>("/reconciliation/run", { source: "hybrid" });
      setRunner(res?.run_id);
      await new Promise((r) => setTimeout(r, 500));
      await fetchCases();
    } catch (e) {
      console.error(e);
    }
    setRunning(false);
  };

  const statusBadge = (status: string) => {
    const map: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
      AUTO_RESOLVED: "success",
      RESOLVED: "success",
      MATCHED: "secondary",
      EXCEPTION: "destructive",
      HUMAN_REVIEW: "warning",
      UNPROCESSED: "outline",
      REJECTED: "destructive",
    };
    return <Badge variant={map[status] || "default"}>{status}</Badge>;
  };

  const riskBadge = (risk: string) => {
    const map: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
      LOW: "success",
      MEDIUM: "warning",
      HIGH: "destructive",
      CRITICAL: "destructive",
    };
    return <Badge variant={map[risk] || "default"}>{risk}</Badge>;
  };

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reconciliation</h1>
          <p className="text-sm text-gray-500">Manage reconciliation cases</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchCases}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
          <Button size="sm" onClick={runReconciliation} disabled={running}>
            <Play className="mr-1 h-4 w-4" />
            {running ? "Running..." : "Run Reconciliation"}
          </Button>
        </div>
      </div>

      {runner && (
        <Card className="mb-4 border-emerald-200 bg-emerald-50">
          <CardContent className="pt-4">
            <p className="text-sm text-emerald-700">Reconciliation run {runner} completed successfully.</p>
          </CardContent>
        </Card>
      )}

      <div className="mb-4 flex gap-2">
        <select
          className="rounded-md border px-3 py-2 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="AUTO_RESOLVED">Auto-Resolved</option>
          <option value="EXCEPTION">Exception</option>
          <option value="HUMAN_REVIEW">Human Review</option>
          <option value="MATCHED">Matched</option>
          <option value="RESOLVED">Resolved</option>
          <option value="REJECTED">Rejected</option>
          <option value="UNPROCESSED">Unprocessed</option>
        </select>
        <select
          className="rounded-md border px-3 py-2 text-sm"
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
        >
          <option value="">All Risk Levels</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs text-gray-500">
                  <th className="px-4 py-3 font-medium">Case ID</th>
                  <th className="px-4 py-3 font-medium">Records</th>
                  <th className="px-4 py-3 font-medium">Amount</th>
                  <th className="px-4 py-3 font-medium">Outcome</th>
                  <th className="px-4 py-3 font-medium">Match Score</th>
                  <th className="px-4 py-3 font-medium">Risk</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                  <th className="px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {(data?.cases ?? []).map((c) => (
                  <tr key={c.case_id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{c.case_id}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {c.related_record_ids?.length ?? 0} records
                    </td>
                    <td className="px-4 py-3 font-medium">
                      {((c.amount ?? 0) / 100).toLocaleString("en-IN", { style: "currency", currency: c.currency || "INR" })}
                    </td>
                    <td className="px-4 py-3 text-xs">{c.outcome_type || "-"}</td>
                    <td className="px-4 py-3 text-xs">{c.match_score?.toFixed(1)}</td>
                    <td className="px-4 py-3">{riskBadge(c.risk)}</td>
                    <td className="px-4 py-3">{statusBadge(c.status)}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{c.source}</td>
                    <td className="px-4 py-3">
                      <Link href={`/exceptions/${c.case_id}`}>
                        <Button variant="ghost" size="sm">
                          View <ArrowRight className="ml-1 h-3 w-3" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
                {(data?.cases?.length ?? 0) === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-400">
                      No cases found. Run reconciliation to generate cases.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </DashboardLayout>
  );
}

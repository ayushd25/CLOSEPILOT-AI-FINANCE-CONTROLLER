"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { ArrowRight, RefreshCw } from "lucide-react";

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

function ExceptionsContent() {
  const searchParams = useSearchParams();
  const selected = searchParams.get("id");
  const [data, setData] = useState<CasesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState("");

  const fetchCases = async () => {
    setLoading(true);
    try {
      // Actionable open cases: EXCEPTION + agent-staged HUMAN_REVIEW.
      const [exc, rev] = await Promise.all([
        api.get<CasesResponse>(`/reconciliation/cases?status=EXCEPTION&${riskFilter ? `risk=${riskFilter}&` : ""}limit=100`),
        api.get<CasesResponse>(`/reconciliation/cases?status=HUMAN_REVIEW&${riskFilter ? `risk=${riskFilter}&` : ""}limit=100`),
      ]);
      const merged: CaseItem[] = [...exc.cases, ...rev.cases];
      // Sort by risk priority and amount
      const priority = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      merged.sort((a, b) => {
        const pa = priority[a.risk as keyof typeof priority] ?? 4;
        const pb = priority[b.risk as keyof typeof priority] ?? 4;
        if (pa !== pb) return pa - pb;
        return (b.amount ?? 0) - (a.amount ?? 0);
      });
      setData({ total: merged.length, cases: merged });
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchCases();
  }, [riskFilter]);

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
          <h1 className="text-2xl font-bold text-gray-900">Exceptions</h1>
          <p className="text-sm text-gray-500">
            Exceptions prioritized by risk and monetary impact
            {selected && <span className="ml-2 text-emerald-600">— viewing case {selected}</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="rounded-md border px-3 py-2 text-sm"
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
          >
            <option value="">All Risks</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
          <Button variant="outline" size="sm" onClick={fetchCases}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {(data?.cases ?? []).map((c) => (
                <Link
                  key={c.case_id}
                  href={`/exceptions/${c.case_id}`}
                  className={`flex items-center justify-between p-4 transition-colors hover:bg-gray-50 ${selected === c.case_id ? "bg-emerald-50" : ""}`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-medium text-gray-700">{c.case_id}</span>
                      {riskBadge(c.risk)}
                      <Badge variant="secondary">{c.outcome_type || "unknown"}</Badge>
                      <Badge variant={c.status === "HUMAN_REVIEW" ? "warning" : "default"}>
                        {c.status === "HUMAN_REVIEW" ? "Human Review" : "Exception"}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                      {((c.amount ?? 0) / 100).toLocaleString("en-IN", { style: "currency", currency: c.currency || "INR" })}
                      {" · "}
                      {c.related_record_ids?.length ?? 0} related records
                    </p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-gray-300" />
                </Link>
              ))}
              {(data?.cases?.length ?? 0) === 0 && (
                <p className="p-8 text-center text-sm text-gray-400">
                  No exceptions found. Run reconciliation to generate cases.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </DashboardLayout>
  );
}

export default function Exceptions() {
  return (
    <Suspense>
      <ExceptionsContent />
    </Suspense>
  );
}

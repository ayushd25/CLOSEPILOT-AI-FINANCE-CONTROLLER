"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { History } from "lucide-react";

interface AuditEventItem {
  event_id: string;
  case_id?: string;
  event_type: string;
  actor_type: string;
  actor_id?: string;
  detail?: string;
  timestamp: string;
  evidence_ids: string[];
  policy_decision?: { decision: string };
  correlation_id?: string;
}

interface AuditResponse {
  total: number;
  events: AuditEventItem[];
}

const eventColors: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  CASE_CREATED: "secondary",
  MATCH_PROPOSED: "outline",
  AI_INVESTIGATION_STARTED: "warning",
  AI_INVESTIGATION_COMPLETED: "warning",
  POLICY_EVALUATED: "outline",
  AUTO_RESOLVED: "success",
  HUMAN_APPROVED: "success",
  HUMAN_REJECTED: "destructive",
  EXCEPTION_CREATED: "destructive",
  SYNC_STARTED: "secondary",
  SYNC_COMPLETED: "success",
};

export default function AuditTrail() {
  const [data, setData] = useState<AuditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [caseFilter, setCaseFilter] = useState("");

  const load = async (caseId?: string) => {
    setLoading(true);
    try {
      const path = caseId ? `/audit/cases/${caseId}` : "/audit";
      const res = await api.get<AuditResponse>(path);
      setData(res);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (caseFilter) {
      load(caseFilter);
    } else {
      load();
    }
  }, [caseFilter]);

  return (
    <DashboardLayout>
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
          <History className="h-5 w-5 text-gray-500" />
          Audit Trail
        </h1>
        <p className="text-sm text-gray-500">Append-only event timeline with full provenance</p>
      </div>

      <div className="mb-4">
        <input
          placeholder="Filter by Case ID (optional)"
          value={caseFilter}
          onChange={(e) => setCaseFilter(e.target.value)}
          className="h-10 w-full max-w-md rounded-md border px-3 text-sm"
        />
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
              {(data?.events ?? []).map((event) => (
                <div key={event.event_id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant={eventColors[event.event_type] || "default"}>
                        {event.event_type}
                      </Badge>
                      <span className="text-xs text-gray-500">{event.actor_type}</span>
                      {event.actor_id && (
                        <span className="text-xs text-gray-400">actor: {event.actor_id}</span>
                      )}
                    </div>
                    <time className="text-xs text-gray-400">
                      {new Date(event.timestamp).toLocaleString()}
                    </time>
                  </div>
                  <p className="mt-1 text-sm text-gray-600">{event.detail || "no detail"}</p>
                  {event.case_id && <p className="font-mono text-[10px] text-gray-400">case: {event.case_id}</p>}
                  {event.policy_decision && (
                    <p className="mt-1 text-xs text-gray-500">
                      Policy: <Badge variant="outline">{event.policy_decision.decision}</Badge>
                    </p>
                  )}
                </div>
              ))}
              {(data?.events?.length ?? 0) === 0 && (
                <p className="p-8 text-center text-sm text-gray-400">No audit events found.</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </DashboardLayout>
  );
}

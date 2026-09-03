"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { Database, RefreshCw } from "lucide-react";

interface RazorpayStatus {
  connected: boolean;
  mode: string;
  payments: number;
  settlements: number;
  recon_events: number;
}

interface SyncRun {
  sync_run_id: string;
  source: string;
  started_at: string;
  completed_at: string;
  status: string;
  fetched: number;
  inserted: number;
  updated: number;
  errors: number;
  duration_seconds: number;
}

interface SyncRunsResponse {
  runs: SyncRun[];
}

interface Config {
  mode: string;
  key_id_configured: boolean;
  secret_configured: boolean;
  page_size: number;
}

export default function DataSources() {
  const [status, setStatus] = useState<RazorpayStatus | null>(null);
  const [runs, setRuns] = useState<SyncRun[]>([]);
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [s, r, c] = await Promise.all([
        api.get<RazorpayStatus>("/integrations/razorpay/status"),
        api.get<SyncRunsResponse>("/integrations/razorpay/sync-runs"),
        api.get<Config>("/integrations/razorpay/configuration"),
      ]);
      setStatus(s);
      setRuns(r.runs || []);
      setConfig(c);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const syncNow = async () => {
    setSyncing(true);
    try {
      await api.post("/integrations/razorpay/sync");
      await load();
    } catch (e) {
      console.error(e);
    }
    setSyncing(false);
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Database className="h-5 w-5 text-gray-500" />
            Data Sources
          </h1>
          <p className="text-sm text-gray-500">Razorpay Test Mode and synthetic data</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="mr-1 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {loading ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Razorpay Test Mode</CardTitle>
              <CardDescription>Test Mode API integration</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Connection Status</span>
                <Badge variant={status?.connected ? "success" : "warning"}>
                  {status?.connected ? "Connected" : "Not Connected"}
                </Badge>
              </div>
              {!status?.connected && (
                <p className="mt-2 text-xs text-gray-400">
                  Configure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in environment to enable sync.
                </p>
              )}
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Payments</span>
                  <span className="font-medium">{status?.payments ?? 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Settlements</span>
                  <span className="font-medium">{status?.settlements ?? 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Recon Events</span>
                  <span className="font-medium">{status?.recon_events ?? 0}</span>
                </div>
              </div>

              <div className="mt-4 border-t pt-4">
                <Button variant="outline" size="sm" onClick={syncNow} disabled={syncing || !status?.connected} className="w-full">
                  {syncing ? "Syncing..." : "Sync Now"}
                </Button>
              </div>

              {config && (
                <div className="mt-4 border-t pt-4 text-xs text-gray-400">
                  <p>Mode: {config.mode === "test" ? "Test Mode (safe)" : config.mode}</p>
                  <p>Key ID configured: {config.key_id_configured ? "Yes" : "No"}</p>
                  <p>Secret configured: {config.secret_configured ? "Yes" : "No"}</p>
                  <p>Page size: {config.page_size}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Syncs</CardTitle>
              <CardDescription>Sync run history</CardDescription>
            </CardHeader>
            <CardContent>
              {runs.length === 0 && (
                <p className="text-sm text-gray-400">No sync runs yet.</p>
              )}
              <div className="space-y-2">
                {runs.slice(0, 5).map((r) => (
                  <div key={r.sync_run_id} className="rounded-md border p-3">
                    <div className="flex items-center justify-between">
                      <Badge variant={r.status === "completed" ? "success" : r.status === "failed" ? "destructive" : "warning"}>
                        {r.status}
                      </Badge>
                      <span className="text-xs text-gray-400">
                        {new Date(r.started_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="mt-2 grid grid-cols-4 gap-2 text-center text-xs">
                      <div>
                        <p className="font-semibold">{r.fetched}</p>
                        <p className="text-gray-400">Fetched</p>
                      </div>
                      <div>
                        <p className="font-semibold">{r.inserted}</p>
                        <p className="text-gray-400">Inserted</p>
                      </div>
                      <div>
                        <p className="font-semibold">{r.updated}</p>
                        <p className="text-gray-400">Updated</p>
                      </div>
                      <div>
                        <p className="font-semibold text-red-500">{r.errors}</p>
                        <p className="text-gray-400">Errors</p>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-gray-400">{r.duration_seconds?.toFixed(1)}s</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </DashboardLayout>
  );
}

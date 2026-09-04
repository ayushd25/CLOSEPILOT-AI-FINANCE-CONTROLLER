"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { RefreshCw, Save, RotateCcw } from "lucide-react";

interface Thresholds {
  confidence_threshold: number;
  max_auto_tolerance: number;
  high_impact_threshold: number;
  min_evidence_ids: number;
  auto_close_match_score: number;
}

interface Toggles {
  enforce_high_impact_gate: boolean;
  auto_close_medium_risk: boolean;
  auto_close_high_risk: boolean;
  enforce_multi_candidate_gate: boolean;
  enforce_discrepancy_tolerance: boolean;
  require_low_risk_for_deterministic_auto_close: boolean;
}

interface PolicyConfig {
  version: number;
  enabled: boolean;
  thresholds: Thresholds;
  toggles: Toggles;
  description: string;
  updated_at: string;
  updated_by: string;
  change_note: string;
}

interface Change {
  field: string;
  from: unknown;
  to: unknown;
}

const THRESHOLD_FIELDS: { key: keyof Thresholds; label: string; hint: string; unit?: string }[] = [
  { key: "confidence_threshold", label: "Confidence threshold", hint: "Min AI confidence (0–1) to auto-close", unit: "" },
  { key: "max_auto_tolerance", label: "Max auto tolerance", hint: "Max amount discrepancy (minor units) allowed for auto-close", unit: "" },
  { key: "high_impact_threshold", label: "High impact threshold", hint: "Amount (minor units) above which human review is required", unit: "" },
  { key: "min_evidence_ids", label: "Min evidence IDs", hint: "Min linked evidence items required to auto-close", unit: "" },
  { key: "auto_close_match_score", label: "Auto-close match score", hint: "Deterministic match score needed to auto-close", unit: "" },
];

const TOGGLE_FIELDS: { key: keyof Toggles; label: string; hint: string }[] = [
  { key: "enforce_high_impact_gate", label: "Enforce high-impact gate", hint: "Route high-value cases to human review" },
  { key: "auto_close_medium_risk", label: "Allow medium-risk auto-close", hint: "Permit AI to auto-close MEDIUM risk cases (higher risk)" },
  { key: "auto_close_high_risk", label: "Allow high-risk auto-close", hint: "Permit AI to auto-close HIGH/CRITICAL risk cases (very high risk)" },
  { key: "enforce_multi_candidate_gate", label: "Enforce multi-candidate gate", hint: "Send ambiguous (multiple candidate) cases to human review" },
  { key: "enforce_discrepancy_tolerance", label: "Enforce discrepancy tolerance", hint: "Block auto-close when the amount diff exceeds tolerance" },
  { key: "require_low_risk_for_deterministic_auto_close", label: "Require low risk for deterministic auto-close", hint: "Deterministic (no-AI) auto-close only for LOW risk cases" },
];

function PolicyEditor() {
  const [config, setConfig] = useState<PolicyConfig | null>(null);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [changes, setChanges] = useState<Change[]>([]);
  const [changeNote, setChangeNote] = useState("");

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await api.get<PolicyConfig>("/policy");
      setConfig(res);
      setDirty(false);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const patchThreshold = (key: keyof Thresholds, raw: string) => {
    if (!config) return;
    const num = parseFloat(raw);
    const value = Number.isFinite(num) ? num : config.thresholds[key];
    setConfig({ ...config, thresholds: { ...config.thresholds, [key]: value } });
    setDirty(true);
  };

  const patchToggle = (key: keyof Toggles, value: boolean) => {
    if (!config) return;
    setConfig({ ...config, toggles: { ...config.toggles, [key]: value } });
    setDirty(true);
  };

  const resetToDefaults = async () => {
    try {
      const defaults = await api.get<PolicyConfig>("/policy/defaults");
      setConfig(defaults);
      setDirty(true);
      setMessage("Default values loaded. Click Save to apply.");
    } catch (e) {
      console.error(e);
    }
  };

  const save = async () => {
    if (!config) return;
    setSaving(true);
    setMessage("");
    try {
      const res = await api.put<{ config: PolicyConfig; changes: Change[]; version: number }>("/policy", {
        thresholds: config.thresholds,
        toggles: config.toggles,
        updated_by: localStorage.getItem("closepilot_role") || "admin",
        change_note: changeNote || "Policy update via UI",
      });
      setConfig(res.config);
      setChanges(res.changes || []);
      setDirty(false);
      setMessage(`Saved. Policy now at version ${res.config.version}.`);
    } catch (e) {
      setMessage(`Save failed: ${e instanceof Error ? e.message : String(e)}`);
    }
    setSaving(false);
  };

  const fmt = (v: unknown) => (typeof v === "boolean" ? (v ? "on" : "off") : JSON.stringify(v));

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Policy Configuration</h1>
          <p className="text-sm text-gray-500">
            Live ruleset. Edits take effect at runtime — the next evaluation reads this config.
            {config && (
              <span className="ml-2 text-emerald-600">
                v{config.version} · {config.updated_by} · {new Date(config.updated_at).toLocaleString()}
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={resetToDefaults}>
            <RotateCcw className="mr-1 h-4 w-4" />
            Load Defaults
          </Button>
          <Button variant="outline" size="sm" onClick={fetchConfig}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {message && (
        <div className={`mb-4 rounded-md border px-4 py-2 text-sm ${message.startsWith("Save failed") ? "border-red-200 bg-red-50 text-red-600" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
          {message}
        </div>
      )}

      {loading && !config ? (
        <div className="space-y-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-24" />
        </div>
      ) : config ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-gray-700">Thresholds</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {THRESHOLD_FIELDS.map((f) => (
                <div key={f.key}>
                  <label className="mb-1 block text-xs font-medium text-gray-600">{f.label}</label>
                  <input
                    type="number"
                    step="any"
                    value={config.thresholds[f.key]}
                    onChange={(e) => patchThreshold(f.key, e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                  <p className="mt-1 text-xs text-gray-400">{f.hint}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-gray-700">Rule Gates</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {TOGGLE_FIELDS.map((f) => (
                <label key={f.key} className="flex cursor-pointer items-start justify-between rounded-md border border-gray-200 p-3 hover:bg-gray-50">
                  <div className="pr-4">
                    <p className="text-sm font-medium text-gray-800">{f.label}</p>
                    <p className="text-xs text-gray-400">{f.hint}</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.toggles[f.key]}
                    onChange={(e) => patchToggle(f.key, e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-gray-300"
                  />
                </label>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <label className="mb-1 block text-xs font-medium text-gray-600">Change note (audit trail)</label>
              <input
                value={changeNote}
                onChange={(e) => setChangeNote(e.target.value)}
                placeholder="e.g. Relax tolerance for settlement fee cases"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
              <div className="mt-3 flex items-center justify-between">
                <p className={`text-sm ${dirty ? "text-amber-600" : "text-gray-400"}`}>
                  {dirty ? "Unsaved changes" : "No pending changes"}
                </p>
                <Button onClick={save} disabled={saving || !dirty}>
                  <Save className="mr-1 h-4 w-4" />
                  {saving ? "Saving…" : "Save & Apply"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {changes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-gray-700">Last change</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="divide-y">
                  {changes.map((c) => (
                    <div key={c.field} className="flex items-center justify-between py-2 text-sm">
                      <span className="font-mono text-xs text-gray-600">{c.field}</span>
                      <span className="flex items-center gap-2 text-gray-500">
                        <Badge variant="secondary">{fmt(c.from)}</Badge>
                        <span>→</span>
                        <Badge variant="success">{fmt(c.to)}</Badge>
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : null}
    </DashboardLayout>
  );
}

export default function Policies() {
  return <PolicyEditor />;
}
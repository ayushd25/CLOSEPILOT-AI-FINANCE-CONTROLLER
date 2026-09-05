"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { Play, RefreshCw, Receipt, Search, ExternalLink, Loader2 } from "lucide-react";

interface TaxMetrics {
  checked: number;
  verified: number;
  exceptions: number;
  human_review: number;
  match_rate: number;
}

interface TaxMatch {
  match_id: string;
  tax_line_id: string | null;
  reference: string | null;
  transaction_id: string;
  invoice_id: string | null;
  currency: string;
  gross_amount: number;
  taxable_amount: number;
  tax_rate: number | null;
  expected_tax: number;
  recorded_tax: number;
  difference: number;
  tolerance: number;
  fee_amount: number;
  status: "VERIFIED" | "EXCEPTION" | "HUMAN_REVIEW";
  reason_codes: string[];
  calculation: string;
  related_record_ids: string[];
  evidence_ids: string[];
  case_id: string | null;
  ai_analysis: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
  reviewed_by: string | null;
  review_note: string | null;
}

interface TaxListResponse {
  total: number;
  matches: TaxMatch[];
}

interface RunSummary {
  processed: number;
  skipped: number;
  verified: number;
  exceptions: number;
  human_review: number;
}

const inr = (paise: number) =>
  (paise / 100).toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

const STATUSES: Array<TaxMatch["status"] | "ALL"> = ["ALL", "VERIFIED", "EXCEPTION", "HUMAN_REVIEW"];

const statusBadge: Record<TaxMatch["status"], "success" | "destructive" | "warning"> = {
  VERIFIED: "success",
  EXCEPTION: "destructive",
  HUMAN_REVIEW: "warning",
};

export default function TaxMatcherPage() {
  const [metrics, setMetrics] = useState<TaxMetrics | null>(null);
  const [matches, setMatches] = useState<TaxMatch[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<TaxMatch["status"] | "ALL">("ALL");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<TaxMatch | null>(null);
  const [runSummary, setRunSummary] = useState<RunSummary | null>(null);

  const load = useCallback(async (st?: TaxMatch["status"] | "ALL", q?: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (st && st !== "ALL") params.set("status", st);
      if (q) params.set("search", q);
      params.set("limit", "200");
      const [m, l] = await Promise.all([
        api.get<TaxMetrics>("/reconciliation/tax-lines/metrics"),
        api.get<TaxListResponse>(`/reconciliation/tax-lines?${params.toString()}`),
      ]);
      setMetrics(m);
      setMatches(l.matches);
      setTotal(l.total);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load(status, search);
  }, [load, status]);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await api.post<RunSummary>("/reconciliation/tax-lines/run?ai=false");
      setRunSummary(res);
      await load(status, search);
    } catch (e) {
      console.error(e);
    }
    setRunning(false);
  };

  const openDetail = async (m: TaxMatch) => {
    try {
      const fresh = await api.get<TaxMatch>(`/reconciliation/tax-lines/${m.match_id}`);
      setDetail(fresh);
    } catch (e) {
      setDetail(m);
    }
  };

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tax-Line Matcher</h1>
          <p className="text-sm text-gray-500">
            Verifies recorded tax against expected tax — gross minus settlement minus fee, or taxable × tax rate
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={handleRun} disabled={running}>
            {running ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Play className="mr-1 h-4 w-4" />}
            {running ? "Matching…" : "Run matcher"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => load(status, search)}>
            <RefreshCw className="mr-1 h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      {runSummary && (
        <div className="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Run complete — {runSummary.processed} line(s) checked, {runSummary.verified} verified,{" "}
          {runSummary.exceptions} exceptions, {runSummary.human_review} in human review
          {runSummary.skipped > 0 ? `, ${runSummary.skipped} orphan tax record(s) skipped` : ""}.
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <MetricCard label="Lines Checked" value={metrics?.checked ?? 0} />
        <MetricCard label="Verified" value={metrics?.verified ?? 0} />
        <MetricCard label="Exceptions" value={metrics?.exceptions ?? 0} />
        <MetricCard label="Human Review" value={metrics?.human_review ?? 0} />
        <MetricCard label="Match Rate" value={`${((metrics?.match_rate ?? 0) * 100).toFixed(1)}%`} sublabel="Verified / checked" />
      </div>

      <Card className="mt-6">
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Receipt className="h-4 w-4 text-emerald-600" /> Tax lines
            </CardTitle>
            <CardDescription>{total} result(s) · click a row for calculation & evidence</CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="flex rounded-md border">
              {STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => setStatus(s)}
                  className={`px-3 py-1.5 text-xs font-medium ${
                    status === s
                      ? "bg-emerald-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {s === "ALL" ? "All" : s.replace("_", " ")}
                </button>
              ))}
            </div>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search tx / ref / invoice…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") load(status, search);
                }}
                className="w-56 pl-8"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="space-y-2 p-4">
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-14" />
              ))}
            </div>
          ) : matches.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Receipt className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-3 text-sm text-gray-500">
                No tax lines found. Run the matcher to verify recorded tax against expected tax for every
                tax-bearing transaction.
              </p>
            </div>
          ) : (
            <div className="divide-y">
              <div className="hidden grid-cols-12 gap-3 px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400 md:grid">
                <span className="col-span-2">Reference</span>
                <span className="col-span-2">Transaction</span>
                <span className="col-span-2">Invoice</span>
                <span className="col-span-1 text-right">Taxable</span>
                <span className="col-span-1">Rate</span>
                <span className="col-span-1 text-right">Δ tax</span>
                <span className="col-span-1">Status</span>
                <span className="col-span-2 text-right">Confidence</span>
              </div>
              {matches.map((m) => (
                <button
                  key={m.match_id}
                  onClick={() => openDetail(m)}
                  className="grid w-full grid-cols-1 gap-2 px-4 py-3 text-left transition-colors hover:bg-gray-50 md:grid-cols-12 md:gap-3 md:items-center"
                >
                  <span className="col-span-2 truncate text-sm font-medium text-gray-900">{m.reference || "—"}</span>
                  <span className="col-span-2 truncate text-sm text-gray-600">{m.transaction_id}</span>
                  <span className="col-span-2 truncate text-sm text-gray-600">{m.invoice_id || "—"}</span>
                  <span className="col-span-1 text-right text-sm text-gray-600">{inr(m.taxable_amount)}</span>
                  <span className="col-span-1 text-sm text-gray-600">{m.tax_rate != null ? `${m.tax_rate}%` : "—"}</span>
                  <span
                    className={`col-span-1 text-right text-sm font-semibold ${
                      m.difference === 0 ? "text-gray-600" : "text-red-600"
                    }`}
                  >
                    {inr(m.difference)}
                  </span>
                  <span className="col-span-1">
                    <Badge variant={statusBadge[m.status]}>{m.status.replace("_", " ")}</Badge>
                  </span>
                  <span className="col-span-2 text-right text-sm text-gray-600">
                    {(m.confidence * 100).toFixed(0)}%
                  </span>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Modal open={!!detail} onClose={() => setDetail(null)} title={`Tax line ${detail?.transaction_id ?? ""}`}>
        {detail && <TaxMatchDetail match={detail} onReviewed={(updated) => {
          setDetail(updated);
          setMatches((prev) => prev.map((p) => (p.match_id === updated.match_id ? updated : p)));
          load(status, search);
        }} />}
      </Modal>
    </DashboardLayout>
  );
}

function TaxMatchDetail({
  match,
  onReviewed,
}: {
  match: TaxMatch;
  onReviewed: (m: TaxMatch) => void;
}) {
  const [action, setAction] = useState<TaxMatch["status"]>(match.status);
  const [note, setNote] = useState(match.review_note ?? "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.post<TaxMatch>(
        `/reconciliation/tax-lines/${match.match_id}/review`,
        { action, note },
      );
      onReviewed(updated);
    } catch (e) {
      console.error(e);
    }
    setSaving(false);
  };

  return (
    <div className="space-y-4 text-sm">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <Field label="Gross" value={inr(match.gross_amount)} />
        <Field label="Taxable" value={inr(match.taxable_amount)} />
        <Field label="Rate" value={match.tax_rate != null ? `${match.tax_rate}%` : "legacy gross−net"} />
        <Field label="Expected tax" value={inr(match.expected_tax)} />
        <Field label="Recorded tax" value={inr(match.recorded_tax)} />
        <Field
          label="Difference"
          value={`${match.difference >= 0 ? "+" : ""}${inr(match.difference)}`}
          sub={match.difference === 0 ? "exact match" : match.status === "VERIFIED" ? "within tolerance" : "beyond tolerance"}
        />
        <Field label="Tolerance" value={inr(match.tolerance)} sub={match.status === "VERIFIED" ? "match is within tolerance" : undefined} />
        <Field label="Fee" value={inr(match.fee_amount)} />
        <Field label="Confidence" value={`${(match.confidence * 100).toFixed(0)}%`} />
      </div>

      <div className="rounded-md border bg-gray-50 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Calculation</p>
        <p className="mt-1 font-mono text-xs text-gray-700">{match.calculation || "—"}</p>
      </div>

      {match.reason_codes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {match.reason_codes.map((r) => (
            <Badge key={r} variant="warning">{r}</Badge>
          ))}
        </div>
      )}

      {match.ai_analysis && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50/60 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">AI analysis (advisory)</p>
          <p className="mt-1 text-xs leading-relaxed text-emerald-900">{match.ai_analysis}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="rounded-md border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Evidence</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {match.evidence_ids.length === 0 && <span className="text-xs text-gray-400">None</span>}
            {match.evidence_ids.map((id) => (
              <Badge key={id} variant="secondary" className="max-w-full">
                <span className="truncate">{id}</span>
              </Badge>
            ))}
          </div>
        </div>
        <div className="rounded-md border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Related records</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {match.related_record_ids.length === 0 && <span className="text-xs text-gray-400">None</span>}
            {match.related_record_ids.map((id) => (
              <Badge key={id} variant="secondary"><span className="truncate">{id}</span></Badge>
            ))}
          </div>
          {match.case_id && (
            <Link
              href={`/exceptions/${match.case_id}`}
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-emerald-600 hover:underline"
            >
              View linked case {match.case_id} <ExternalLink className="h-3 w-3" />
            </Link>
          )}
        </div>
      </div>

      <div className="rounded-lg border p-3.5">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Human review</p>
        <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <select
            className="rounded-md border px-3 py-2 text-sm"
            value={action}
            onChange={(e) => setAction(e.target.value as TaxMatch["status"])}
          >
            <option value="VERIFIED">VERIFIED — recorded tax correct</option>
            <option value="EXCEPTION">EXCEPTION — keep as discrepancy</option>
            <option value="HUMAN_REVIEW">HUMAN_REVIEW — needs more analysis</option>
          </select>
          <input
            className="rounded-md border px-3 py-2 text-sm"
            placeholder="Review note…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        <div className="mt-3 flex justify-end">
          <Button size="sm" onClick={save} disabled={saving || action === match.status && note === (match.review_note ?? "")}>
            {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
            Save decision
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-md border p-2.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-gray-900">{value}</p>
      {sub && <p className="text-[11px] text-gray-400">{sub}</p>}
    </div>
  );
}
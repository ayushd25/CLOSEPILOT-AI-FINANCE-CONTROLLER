"use client";

import { useCallback, useEffect, useState } from "react";
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
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { RefreshCw, TrendingUp, Sparkles, Info, AlertTriangle } from "lucide-react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ForecastPoint {
  date: string;
  projected_cash: number;
  risk_adjusted_cash: number;
  lower_bound: number;
  upper_bound: number;
}

interface ForecastComponent {
  category: string;
  label: string;
  amount: number;
  count: number;
  detail: string;
  netted: boolean;
}

interface CashForecast {
  as_of: string;
  horizon_days: number;
  currency: string;
  current_cash: number;
  inflow_expected: number;
  outflow_expected: number;
  risk_holdback: number;
  net_change: number;
  projected_optimistic: number;
  projected_cash: number;
  confidence: number;
  data_quality: {
    days_of_history: number;
    records_used: Record<string, number>;
    settlement_lag_days: number;
    refund_rate: number;
    avg_daily_settlement: number;
    daily_volatility: number;
  };
  components: ForecastComponent[];
  points: ForecastPoint[];
  assumptions: string[];
  commentary?: string | null;
}

const inr = (paise: number) =>
  (paise / 100).toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

const HORIZONS = [7, 14, 30] as const;

export default function CashForecastPage() {
  const [data, setData] = useState<CashForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [horizon, setHorizon] = useState<number>(7);

  const load = useCallback(async (h: number) => {
    setLoading(true);
    try {
      const res = await api.get<CashForecast>(`/forecast?horizon=${h}&ai=true`);
      setData(res);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load(horizon);
  }, [horizon, load]);

  const empty = data && (data.data_quality.days_of_history === 0 || data.current_cash === 0 && data.points.length === 0);

  const chartData = (data?.points ?? []).map((p) => ({
    ...p,
    label: new Date(p.date + "T00:00:00Z").toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
  }));

  const inflowComponents = (data?.components ?? []).filter(
    (c) => ["SCHEDULED_SETTLEMENTS", "RECEIVABLES", "PATTERN_FLOW"].includes(c.category),
  );
  const outflowComponents = (data?.components ?? []).filter(
    (c) => ["EXPECTED_REFUNDS", "EXPECTED_ADJUSTMENTS", "EXPECTED_CHARGEBACKS"].includes(c.category),
  );
  const insightComponents = (data?.components ?? []).filter(
    (c) => !inflowComponents.includes(c) && !outflowComponents.includes(c),
  );

  const badgeFor = (category: string) => {
    const map: Record<string, "success" | "warning" | "secondary" | "destructive"> = {
      SCHEDULED_SETTLEMENTS: "success",
      RECEIVABLES: "secondary",
      PATTERN_FLOW: "secondary",
      EXPECTED_REFUNDS: "warning",
      EXPECTED_ADJUSTMENTS: "warning",
      EXPECTED_CHARGEBACKS: "destructive",
      RISK_HOLDBACK: "destructive",
    };
    return map[category] || "secondary";
  };

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cash Forecast</h1>
          <p className="text-sm text-gray-500">
            Deterministic forward cash projection from loaded records · horizon {horizon} days
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border">
            {HORIZONS.map((h) => (
              <button
                key={h}
                onClick={() => setHorizon(h)}
                className={`px-3 py-1.5 text-sm font-medium ${
                  horizon === h ? "bg-emerald-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                {h}d
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={() => load(horizon)}>
            <RefreshCw className="mr-1 h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      {loading && !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <Skeleton className="h-72" />
        </div>
      ) : empty ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 px-6 py-16 text-center">
            <Info className="h-8 w-8 text-gray-300" />
            <p className="text-sm text-gray-500">
              No bank/settlement history loaded yet. Generate a dataset in Data Sources, then return here —
              every number on this chart is computed from your records, never invented.
            </p>
            <a href="/sources" className="text-sm font-medium text-emerald-600 hover:underline">
              Go to Data Sources →
            </a>
          </CardContent>
        </Card>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <MetricCard label="Current Cash" value={inr(data.current_cash)} sublabel="Settled in bank" />
            <MetricCard label="Projected (Conservative)" value={inr(data.projected_cash)} sublabel={`Forecast ${data.horizon_days}d`} />
            <MetricCard label="Optimistic Projection" value={inr(data.projected_optimistic)} sublabel="Before risk holdback" />
            <MetricCard
              label="Net Change"
              value={`${data.net_change >= 0 ? "+" : ""}${inr(data.net_change)}`}
              sublabel="Inflows − outflows"
            />
            <MetricCard label="Confidence" value={`${(data.confidence * 100).toFixed(0)}%`} sublabel="From data quality" />
          </div>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-600" />
                Projected cash curve · {data.horizon_days} days
              </CardTitle>
              <CardDescription>Emerald = optimistic path · amber dashes = after {inr(data.risk_holdback)} risk holdback</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      stroke="#9ca3af"
                      tickFormatter={(v: number) => inr(v)}
                      domain={["auto", "auto"]}
                    />
                    <Tooltip
                      formatter={(value: number | string, name: string) => [
                        inr(Number(value)),
                        name === "projected_cash" ? "Optimistic" : name === "risk_adjusted_cash" ? "After holdback" : name,
                      ]}
                      labelFormatter={(label) => `Date: ${label}`}
                    />
                    <Area type="monotone" dataKey="upper_bound" stroke="none" fill="#d1fae5" fillOpacity={0.5} name="Upper bound" />
                    <Line type="monotone" dataKey="projected_cash" stroke="#059669" strokeWidth={2} dot={false} name="Optimistic" />
                    <Line type="monotone" dataKey="lower_bound" stroke="#d1fae5" strokeWidth={1} dot={false} name="Lower bound" />
                    <Line type="monotone" dataKey="risk_adjusted_cash" stroke="#d97706" strokeWidth={2} strokeDasharray="5 4" dot={false} name="After holdback" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-gray-400">
                All amounts are in minor units (paise) on the API; displayed in INR. Projected figures are deterministic model output.
              </p>
            </CardContent>
          </Card>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Inflows</CardTitle>
                <CardDescription>{inr(data.inflow_expected)} expected · component breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <ComponentList components={inflowComponents} badgeFor={badgeFor} inr={inr} />
                {inflowComponents.length === 0 && <p className="text-sm text-gray-400">No inflow components.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Outflows</CardTitle>
                <CardDescription>{inr(data.outflow_expected)} expected · component breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <ComponentList components={outflowComponents} badgeFor={badgeFor} inr={inr} />
                {outflowComponents.length === 0 && <p className="text-sm text-gray-400">No outflow components.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Insights</CardTitle>
                <CardDescription>Risk & transparency items</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {insightComponents.map((c) => (
                  <div key={c.category} className="rounded-md border p-3">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-sm font-medium">
                        {c.category === "RISK_HOLDBACK" ? <AlertTriangle className="h-4 w-4 text-amber-500" /> : <Info className="h-4 w-4 text-emerald-600" />}
                        {c.label}
                      </span>
                      <Badge variant={badgeFor(c.category)}>{inr(c.amount)}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">{c.detail}</p>
                  </div>
                ))}
                {insightComponents.length === 0 && <p className="text-sm text-gray-400">No insight components.</p>}
              </CardContent>
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-4 w-4 text-emerald-600" /> AI Commentary
                </CardTitle>
                <CardDescription>Explains the computed figures only — never invents numbers</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-gray-700">{data.commentary || "No commentary."}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Assumptions & Data Quality</CardTitle>
                <CardDescription>
                  {data.data_quality.days_of_history} days of history · {data.data_quality.records_used?.payments ?? 0} payments ·{" "}
                  {data.data_quality.records_used?.settlements ?? 0} settlements · lag{" "}
                  {data.data_quality.settlement_lag_days}d · refund rate {(data.data_quality.refund_rate * 100).toFixed(1)}%
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600">
                  {data.assumptions.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </DashboardLayout>
  );
}

function ComponentList({
  components,
  badgeFor,
  inr,
}: {
  components: ForecastComponent[];
  badgeFor: (c: string) => "success" | "warning" | "secondary" | "destructive";
  inr: (n: number) => string;
}) {
  return (
    <div className="space-y-3">
      {components.map((c) => (
        <div key={c.category} className="rounded-md border p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{c.label}</span>
            <Badge variant={badgeFor(c.category)}>{inr(c.amount)}</Badge>
          </div>
          <p className="mt-1 text-xs text-gray-500">{c.detail}</p>
          {c.count > 0 && <p className="mt-1 text-[11px] text-gray-400">{c.count} item(s)</p>}
        </div>
      ))}
    </div>
  );
}
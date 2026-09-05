"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Landmark,
  ArrowRight,
  BookOpen,
  GitCompareArrows,
  BrainCircuit,
  Sparkles,
  ScanLine,
  GitBranch,
  Receipt,
  FlaskConical,
  History,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const ctaSm =
  "inline-flex h-8 items-center justify-center gap-2 whitespace-nowrap rounded-lg px-3 text-xs font-medium transition-all";
const ctaLg =
  "inline-flex h-11 items-center justify-center gap-2 whitespace-nowrap rounded-lg px-8 text-sm font-medium transition-all";
const ctaPrimary = "bg-emerald-500 text-emerald-950 hover:bg-emerald-400 glow-emerald";
const ctaOutline = "border border-white/15 bg-white/5 text-white hover:border-white/30 hover:bg-white/10";
const ctaSecondary = "bg-white text-[#0A1626] hover:bg-emerald-50";

interface Summary {
  total_records: number;
  total_cases: number;
  reconciled: number;
  auto_resolved: number;
  human_review: number;
  exceptions: number;
}

interface Forecast {
  current_cash: number;
  projected_cash: number;
  risk_holdback: number;
  horizon_days: number;
}

interface TaxMetrics {
  checked: number;
  verified: number;
  exceptions: number;
}

const features = [
  {
    icon: GitCompareArrows,
    title: "Rules-first reconciliation",
    body: "Deterministic matching of payments, settlements and bank transactions — reference, amount and date signals with an explicit confidence score.",
    href: "/reconciliation",
  },
  {
    icon: BrainCircuit,
    title: "AI that investigates, never decides",
    body: "An LLM inspector reads each case and proposes conclusions, risk and actions. It only proposes: the policy engine is the only authorizer.",
    href: "/exceptions",
  },
  {
    icon: GitBranch,
    title: "Policies authorize. Nothing is forced.",
    body: "Auto-close only when rules say LOW risk, within tolerance and fully evidenced. Everything else is staged for a human reviewer.",
    href: "/policies",
  },
  {
    icon: ScanLine,
    title: "Forward cash forecast",
    body: "Deterministic 7/14/30-day cash projection from your loaded records — scheduled settlements, receivables, refunds, and a risk holdback. The AI only explains the numbers.",
    href: "/forecast",
  },
  {
    icon: Receipt,
    title: "Tax-line matcher",
    body: "expected_tax = taxable_amount × tax_rate, verified per line. Discrepancies become cases with evidence and audit, ready for a human to review.",
    href: "/tax",
  },
  {
    icon: FlaskConical,
    title: "Measured, not claimed",
    body: "Generate datasets with hidden ground truth and score precision, recall and auto-resolution in the Evaluation Lab. No magic, no black boxes.",
    href: "/evaluation",
  },
];

const steps = [
  {
    n: "01",
    title: "Load your data",
    body: "Bring in payments, settlements, bank transactions, invoices and tax records. Use the synthetic dataset generator to explore with realistic scenarios.",
  },
  {
    n: "02",
    title: "Reconcile and investigate",
    body: "Run reconciliation to produce cases, then let the AI inspector propose root causes and actions. Every claim is tied to evidence in the graph.",
  },
  {
    n: "03",
    title: "Authorize and audit",
    body: "The policy engine decides what may be auto-closed. Humans review the rest. Every action is appended to the audit trail — replayable, forever.",
  },
];

const inr = (paise: number) =>
  (paise / 100).toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

function LiveStrip() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [tax, setTax] = useState<TaxMetrics | null>(null);

  useEffect(() => {
    const load = async () => {
      const [s, f, t] = await Promise.allSettled([
        api.get<Summary>("/dashboard/summary"),
        api.get<Forecast>("/forecast?horizon=7&ai=false"),
        api.get<TaxMetrics>("/reconciliation/tax-lines/metrics"),
      ]);
      if (s.status === "fulfilled") setSummary(s.value);
      if (f.status === "fulfilled") setForecast(f.value);
      if (t.status === "fulfilled") setTax(t.value);
    };
    load();
  }, []);

  const hasData = (summary?.total_records ?? 0) > 0;
  if (!hasData) {
    return (
      <div className="mx-auto mt-10 max-w-2xl rounded-xl border border-dashed border-white/15 bg-white/5 px-6 py-5 text-center backdrop-blur-sm">
        <p className="text-sm text-slate-300">
          No data loaded yet. Generate a dataset to unlock live numbers on this page.
        </p>
        <Link href="/sources" className={cn(ctaSm, ctaPrimary, "mt-3")}>Generate a dataset →</Link>
      </div>
    );
  }

  const items = [
    { label: "Records ingested", value: summary?.total_records?.toLocaleString("en-IN") ?? "—", accent: false },
    { label: "Reconciled", value: summary?.reconciled?.toLocaleString("en-IN") ?? "—", accent: true },
    { label: "Auto-resolved", value: summary?.auto_resolved?.toLocaleString("en-IN") ?? "—", accent: true },
    { label: "Open cases", value: summary?.human_review !== undefined ? (summary.human_review + summary.exceptions).toLocaleString("en-IN") : "—", accent: false },
    { label: "Forecast (7d)", value: forecast ? inr(forecast.projected_cash) : "—", accent: true },
    { label: "Tax lines checked", value: tax?.checked?.toLocaleString("en-IN") ?? "—", accent: false },
  ];

  return (
    <div className="mx-auto mt-12 grid max-w-4xl grid-cols-2 gap-4 md:grid-cols-3">
      {items.map((it) => (
        <div
          key={it.label}
          className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-4 text-center backdrop-blur-sm transition-colors hover:border-emerald-400/30"
        >
          <p className="text-[11px] font-medium uppercase tracking-widest text-slate-400">{it.label}</p>
          <p className={cn("mt-1.5 text-xl font-bold tabular-nums", it.accent ? "text-emerald-300" : "text-white")}>
            {it.value}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-background font-sans text-foreground">
      {/* Top bar */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#06101D]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-[0_4px_16px_rgba(16,185,129,0.4)]">
              <Landmark className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-bold leading-none tracking-tight text-white">ClosePilot</p>
              <p className="mt-0.5 text-[10px] font-medium uppercase tracking-widest text-emerald-400/90">
                Autonomous Finance Controller
              </p>
            </div>
          </div>
          <nav className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
            <Link className="transition-colors hover:text-white" href="#features">Features</Link>
            <Link className="transition-colors hover:text-white" href="#how">How it works</Link>
            <Link className="transition-colors hover:text-white" href="/forecast">Forecast</Link>
            <Link className="transition-colors hover:text-white" href="/tax">Tax matcher</Link>
          </nav>
          <Link href="/explore" className={cn(ctaSm, ctaPrimary)}>
            Open the app <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-white/5 bg-[#071223] text-white">
        <div className="absolute inset-0 bg-fin-grid" aria-hidden />
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(60% 55% at 50% -12%, rgba(16,185,129,0.22), rgba(16,185,129,0.05) 45%, transparent 70%)",
          }}
          aria-hidden
        />
        <div className="relative mx-auto max-w-4xl px-6 py-24 text-center"
          style={{
            background:
              "radial-gradient(90% 40% at 50% 0%, rgba(16,185,129,0.10), rgba(7,18,35,0) 70%)",
          }}>
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-300">
            <Sparkles className="h-3.5 w-3.5" /> AI Finance Controller for payment reconciliation
          </span>
          <h1 className="mt-6 text-4xl font-extrabold tracking-tighter text-white md:text-6xl">
            Automate what you can prove.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-slate-300">
            ClosePilot reconciles payments, settles discrepancies and forecasts cash — with an AI that
            investigates and proposes, rules that authorize, and an evidence graph that proves every decision.
            Nothing is ever forced through.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/explore" className={cn(ctaLg, ctaPrimary)}>
              Explore ClosePilot <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="/docs" className={cn(ctaLg, ctaOutline)}>
              <BookOpen className="mr-2 h-4 w-4" /> Read the docs
            </Link>
          </div>
          <LiveStrip />
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-24">
        <p className="text-center text-xs font-semibold uppercase tracking-widest text-emerald-600">Capabilities</p>
        <h2 className="mt-3 text-center text-3xl font-bold tracking-tight text-foreground">
          Investigate with AI. Decide with rules. Prove with evidence.
        </h2>
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <Link
              key={f.title}
              href={f.href}
              className="group rounded-2xl border bg-card p-6 shadow-[0_1px_3px_rgba(15,23,42,0.06)] transition-all hover:-translate-y-0.5 hover:border-emerald-500/40 hover:shadow-lg"
            >
              <f.icon className="h-8 w-8 text-emerald-600" />
              <h3 className="mt-4 text-base font-semibold tracking-tight text-foreground">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
              <span className="mt-3 inline-flex items-center text-sm font-medium text-emerald-600">
                Open <ArrowRight className="ml-1 h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-y bg-slate-50/80">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <p className="text-center text-xs font-semibold uppercase tracking-widest text-emerald-600">The loop</p>
          <h2 className="mt-3 text-center text-3xl font-bold tracking-tight text-foreground">How ClosePilot works</h2>
          <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
            {steps.map((s) => (
              <div key={s.n} className="relative rounded-2xl border bg-card p-6 shadow-sm">
                <span className="bg-gradient-to-br from-emerald-500 to-emerald-700 bg-clip-text text-5xl font-extrabold tracking-tight text-transparent">
                  {s.n}
                </span>
                <h3 className="mt-3 text-lg font-semibold tracking-tight text-foreground">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Principle band */}
      <section className="relative overflow-hidden bg-[#0A1626]">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/60 to-transparent" aria-hidden />
        <div
          className="absolute inset-0"
          style={{ background: "radial-gradient(55% 80% at 50% 0%, rgba(16,185,129,0.14), transparent 70%)" }}
          aria-hidden
        />
        <div className="relative mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-6 py-14 text-center md:flex-row md:text-left">
          <div>
            <p className="text-xl font-bold tracking-tight text-white md:text-2xl">
              Models investigate. Rules authorize. Evidence proves.
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Every action is gated by the policy engine and appended to a replayable audit trail.
            </p>
          </div>
          <Link href="/explore" className={cn(ctaLg, ctaSecondary)}>
              Explore ClosePilot <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#06101D]">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 md:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 text-white">
              <Landmark className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-white">ClosePilot</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-slate-400">
            <Link className="transition-colors hover:text-white" href="/explore">Command Center</Link>
            <Link className="transition-colors hover:text-white" href="/docs">Documentation</Link>
            <Link className="transition-colors hover:text-white" href="/evaluation">Evaluation Lab</Link>
            <span className="inline-flex items-center gap-1"><History className="h-3.5 w-3.5" /> Append-only audit trail</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
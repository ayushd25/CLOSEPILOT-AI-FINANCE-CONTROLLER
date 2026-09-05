"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Shield,
  ArrowRight,
  BookOpen,
  GitCompareArrows,
  BrainCircuit,
  Sparkles,
  Scale,
  ScanLine,
  Receipt,
  FlaskConical,
  History,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const ctaSm =
  "inline-flex h-8 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3 text-xs font-medium transition-colors";
const ctaLg =
  "inline-flex h-11 items-center justify-center gap-2 whitespace-nowrap rounded-md px-8 text-sm font-medium transition-colors";
const ctaPrimary = "bg-emerald-600 text-white hover:bg-emerald-700";
const ctaOutline = "border border-gray-300 bg-white text-gray-900 hover:bg-gray-50";
const ctaSecondary = "bg-white text-emerald-700 hover:bg-emerald-50";

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
    icon: Scale,
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
      <div className="mx-auto mt-10 max-w-2xl rounded-xl border border-dashed border-gray-300 bg-white px-6 py-5 text-center shadow-sm">
        <p className="text-sm text-gray-600">
          No data loaded yet. Generate a dataset to unlock live numbers on this page.
        </p>
        <Link href="/sources" className={cn(ctaSm, ctaOutline, "mt-3")}>Generate a dataset →</Link>
      </div>
    );
  }

  const items = [
    { label: "Records ingested", value: summary?.total_records?.toLocaleString("en-IN") ?? "—" },
    { label: "Reconciled", value: summary?.reconciled?.toLocaleString("en-IN") ?? "—" },
    { label: "Auto-resolved", value: summary?.auto_resolved?.toLocaleString("en-IN") ?? "—" },
    { label: "Open cases", value: summary?.human_review !== undefined ? (summary.human_review + summary.exceptions).toLocaleString("en-IN") : "—" },
    { label: "Forecast (7d)", value: forecast ? inr(forecast.projected_cash) : "—" },
    { label: "Tax lines checked", value: tax?.checked?.toLocaleString("en-IN") ?? "—" },
  ];

  return (
    <div className="mx-auto mt-12 grid max-w-4xl grid-cols-2 gap-4 md:grid-cols-3">
      {items.map((it) => (
        <div key={it.label} className="rounded-xl border bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium text-gray-500">{it.label}</p>
          <p className="mt-1 text-xl font-bold text-gray-900">{it.value}</p>
        </div>
      ))}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-900">
      {/* Top bar */}
      <header className="sticky top-0 z-40 border-b bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-emerald-600 text-white">
              <Shield className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-bold leading-none">ClosePilot</p>
              <p className="text-[10px] text-muted-foreground">Autonomous Finance Controller</p>
            </div>
          </div>
          <nav className="hidden items-center gap-6 text-sm text-gray-600 md:flex">
            <Link className="hover:text-gray-900" href="#features">Features</Link>
            <Link className="hover:text-gray-900" href="#how">How it works</Link>
            <Link className="hover:text-gray-900" href="/forecast">Forecast</Link>
            <Link className="hover:text-gray-900" href="/tax">Tax matcher</Link>
          </nav>
          <Link href="/explore" className={cn(ctaSm, ctaPrimary)}>
            Open the app <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b bg-gradient-to-b from-emerald-50/60 to-gray-50">
        <div className="mx-auto max-w-4xl px-6 py-20 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            <Sparkles className="h-3.5 w-3.5" /> AI Finance Controller for payment reconciliation
          </span>
          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-gray-900 md:text-6xl">
            Automate what you can prove.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-gray-600">
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
      <section id="features" className="mx-auto max-w-6xl px-6 py-20">
        <p className="text-center text-xs font-semibold uppercase tracking-widest text-emerald-600">Capabilities</p>
        <h2 className="mt-3 text-center text-3xl font-bold text-gray-900">
          Investigate with AI. Decide with rules. Prove with evidence.
        </h2>
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <Link
              key={f.title}
              href={f.href}
              className="group rounded-2xl border bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              <f.icon className="h-8 w-8 text-emerald-600" />
              <h3 className="mt-4 text-base font-semibold text-gray-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{f.body}</p>
              <span className="mt-3 inline-flex items-center text-sm font-medium text-emerald-600">
                Open <ArrowRight className="ml-1 h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-y bg-white">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <p className="text-center text-xs font-semibold uppercase tracking-widest text-emerald-600">The loop</p>
          <h2 className="mt-3 text-center text-3xl font-bold text-gray-900">How ClosePilot works</h2>
          <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
            {steps.map((s) => (
              <div key={s.n} className="relative rounded-2xl border bg-gray-50/50 p-6">
                <span className="text-4xl font-extrabold text-emerald-200">{s.n}</span>
                <h3 className="mt-3 text-lg font-semibold text-gray-900">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Principle band */}
      <section className="bg-emerald-700">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-6 py-12 text-center md:flex-row md:text-left">
          <div>
            <p className="text-xl font-bold text-white md:text-2xl">
              Models investigate. Rules authorize. Evidence proves.
            </p>
            <p className="mt-2 text-sm text-emerald-100">
              Every action is gated by the policy engine and appended to a replayable audit trail.
            </p>
          </div>
          <Link href="/explore" className={cn(ctaLg, ctaSecondary)}>
              Explore ClosePilot <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 md:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-emerald-500 text-white">
              <Shield className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-semibold text-white">ClosePilot</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-gray-400">
            <Link className="hover:text-white" href="/explore">Command Center</Link>
            <Link className="hover:text-white" href="/docs">Documentation</Link>
            <Link className="hover:text-white" href="/evaluation">Evaluation Lab</Link>
            <span className="inline-flex items-center gap-1"><History className="h-3.5 w-3.5" /> Append-only audit trail</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
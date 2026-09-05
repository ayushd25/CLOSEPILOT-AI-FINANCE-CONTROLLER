"use client";

import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SlidersHorizontal, Bot, ShieldCheck, BookOpen, Compass, Users, Workflow, ListChecks, ScrollText, HelpCircle } from "lucide-react";

function SectionTitle({ icon: Icon, children, id }: { icon: typeof Compass; children: React.ReactNode; id?: string }) {
  return (
    <h2 id={id} className="mt-10 mb-3 flex items-center gap-2 text-xl font-bold text-gray-900">
      <Icon className="h-5 w-5 text-emerald-600" />
      {children}
    </h2>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-gray-200 p-4">
      <p className="mb-1 flex items-center gap-2 text-sm font-semibold text-gray-800">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-600 text-xs font-bold text-white">{n}</span>
        {title}
      </p>
      <div className="pl-8 text-sm text-gray-600">{children}</div>
    </div>
  );
}

const roles = [
  { role: "ADMIN", desc: "Approve, reject, keep-exception, and investigate (full access)." },
  { role: "FINANCE_CONTROLLER", desc: "Same full set as ADMIN — this is the UI default.", recommended: true },
  { role: "REVIEWER", desc: "Approve, reject, keep-exception — cannot run investigations." },
  { role: "VIEWER", desc: "Read-only; no approve/reject/investigate actions." },
];

const sidebarIndex = [
  { href: "/", label: "Landing", desc: "Public landing page and live data summary." },
  { href: "/explore", label: "Command Center", desc: "Operational dashboard, KPIs, risk distribution." },
  { href: "/reconciliation", label: "Reconciliation", desc: "Run reconciliation and inspect generated cases." },
  { href: "/exceptions", label: "Exceptions", desc: "Prioritized actionable cases (EXCEPTION + HUMAN_REVIEW)." },
  { href: "/exceptions/[caseId]", label: "Exception Investigator", desc: "Drill into a single case: investigate, evaluate, act." },
  { href: "/forecast", label: "Cash Forecast", desc: "Deterministic 7/14/30-day forward cash projection." },
  { href: "/tax", label: "Tax-Line Matcher", desc: "Verified tax lines vs. expected tax per record." },
  { href: "/evaluation", label: "Evaluation Lab", desc: "Benchmark your reconciliation against ground truth." },
  { href: "/evidence", label: "Evidence Graph", desc: "Visual record-provenance graph for a case." },
  { href: "/audit", label: "Audit Trail", desc: "Append-only event timeline with full provenance." },
  { href: "/sources", label: "Data Sources", desc: "Generate synthetic financial records." },
  { href: "/policies", label: "Policies", desc: "Edit the live ruleset — applied immediately." },
  { href: "/docs", label: "Documentation", desc: "This guide." },
];

export default function Docs() {
  return (
    <DashboardLayout>
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 border-b border-gray-200 pb-6">
          <div className="flex items-center gap-2 text-emerald-700">
            <BookOpen className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase tracking-wide">ClosePilot Documentation</span>
          </div>
          <h1 className="mt-2 text-3xl font-bold text-gray-900">How to use ClosePilot</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-600">
            A complete guide to navigating the platform, understanding roles and security, and using the reconciliation
            and autonomous agent to analyze, verify, and auto-evaluate your financial transactions.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="success">Models investigate</Badge>
            <Badge variant="default">Rules authorize</Badge>
            <Badge variant="warning">Evidence proves</Badge>
          </div>
        </div>

        {/* Table of contents */}
        <Card>
          <CardContent className="p-4">
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700">
              <ListChecks className="h-4 w-4 text-emerald-600" /> On this page
            </p>
            <div className="grid grid-cols-1 gap-1 text-sm text-emerald-700 sm:grid-cols-2">
              <a href="#navigate" className="hover:underline">1. Navigating the platform</a>
              <a href="#roles" className="hover:underline">2. Roles & permissions</a>
              <a href="#workflow" className="hover:underline">3. Analyze / verify / auto-evaluate transactions</a>
              <a href="#forecast-tax" className="hover:underline">4. Cash forecast & tax-line matcher</a>
              <a href="#agent" className="hover:underline">5. Using the assistive agent</a>
              <a href="#policies" className="hover:underline">6. Policy configuration</a>
              <a href="#audit" className="hover:underline">7. Audit & evidence</a>
              <a href="#troubleshoot" className="hover:underline">8. Troubleshooting</a>
            </div>
          </CardContent>
        </Card>

        {/* 1. Navigation */}
        <SectionTitle id="navigate" icon={Compass}>1. Navigating the platform</SectionTitle>
        <p className="text-sm text-gray-600">
          The left sidebar gives you access to every area. Start at the <strong>Command Center</strong> for a live overview,
          then drill down as needed.
        </p>
        <Card className="mt-3">
          <CardContent className="p-0">
            <div className="divide-y">
              {sidebarIndex.map((s) => (
                <div key={s.href} className="flex items-center justify-between p-3">
                  <div>
                    <a href={s.href} className="font-mono text-xs font-semibold text-emerald-700 hover:underline">{s.label}</a>
                    <p className="text-xs text-gray-500">{s.desc}</p>
                  </div>
                  <Badge variant="secondary">{s.href}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 2. Roles */}
        <SectionTitle id="roles" icon={Users}>2. Roles & permissions</SectionTitle>
        <p className="text-sm text-gray-600">
          Actions are gated by role via the engine. The role is sent with each request; the UI defaults to{" "}
          <strong>FINANCE_CONTROLLER</strong>. Role only gates <em>human</em> actions — the policy engine always enforces authorization.
        </p>
        <Card className="mt-3">
          <CardContent className="p-0">
            <div className="divide-y">
              {roles.map((r) => (
                <div key={r.role} className="flex items-center justify-between p-3">
                  <span className="text-sm font-semibold text-gray-800">
                    {r.role}
                    {r.recommended && <span className="ml-2 text-xs font-normal text-emerald-600">(UI default)</span>}
                  </span>
                  <span className="text-xs text-gray-500">{r.desc}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 3. Workflow */}
        <SectionTitle id="workflow" icon={Workflow}>3. Analyze, verify & auto-evaluate transactions</SectionTitle>
        <div className="mt-3 space-y-3">
          <Step n={1} title="Load data — Data Sources">
            Open <strong>/sources</strong> and <strong>Generate</strong> a synthetic dataset (choose <code>n_cases</code> and a{" "}
            <code>seed</code>). This creates payments, settlements, bank transactions, and more across 20 reconciliation
            scenarios with hidden ground truth.
          </Step>
          <Step n={2} title="Reconcile — Reconciliation">
            Open <strong>/reconciliation</strong> and hit <strong>Run Reconciliation</strong> to turn the financial records into
            reconciliation cases (matched, auto-resolved, exception, or human-review). Filter by status and risk to focus.
          </Step>
          <Step n={3} title="Investigate — Exception Investigator">
            Open a case from <strong>/exceptions</strong> and click <strong>Investigate</strong>. The AI proposes a conclusion
            (<code>MATCH_CONFIRMED</code>, <code>NO_MATCH</code>, <code>EXPLAINED_DISCREPANCY</code>, or{" "}
            <code>INSUFFICIENT_EVIDENCE</code>), a risk level, a confidence, a proposed action, and a root cause. This step is
            strictly read-only — it never mutates the case.
          </Step>
          <Step n={4} title="Evaluate policy — Policy Decision">
            Click <strong>Evaluate Policy</strong> to ask the PolicyEngine whether the proposal may be auto-closed (
            <code>AUTO_CLOSE</code>) or must go to a human (<code>HUMAN_REVIEW</code>). By default, auto-close needs LOW risk,
            confidence at/above the threshold, sufficient evidence, a discrepancy within tolerance, and a single candidate.
          </Step>
          <Step n={6} title="Act & audit — Actions">
            If eligible, use <strong>Approve &amp; Close</strong>; otherwise <strong>Keep Exception</strong> or{" "}
            <strong>Reject Proposal</strong>. Every action is recorded to the <strong>Audit Trail</strong> with the policy
            decision, so you can replay exactly why any case was resolved.
          </Step>
        </div>

        {/* Forecast & Tax */}
        <SectionTitle id="forecast-tax" icon={Compass}>4. Cash Forecast & Tax-line Matcher</SectionTitle>
        <p className="text-sm text-gray-600">
          Two deterministic analytic surfaces built on the same records — no invented numbers.
        </p>
        <Card className="mt-3">
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-md border border-gray-200 p-3">
              <p className="text-sm font-semibold text-gray-800">Cash Forecast (/forecast)</p>
              <p className="mt-1 text-xs text-gray-600">
                Projects cash forward 7/14/30 days from current bank balance, scheduled settlements, receivables,
                refunds/adjustments/chargebacks, and suspends risk holdback from open cases. The AI adds commentary
                that only restates the computed figures. A confidence band reflects data quality.
              </p>
            </div>
            <div className="rounded-md border border-gray-200 p-3">
              <p className="text-sm font-semibold text-gray-800">Tax-line Matcher (/tax)</p>
              <p className="mt-1 text-xs text-gray-600">
                For every tax-bearing line, expected tax is derived (gross − settlement − fee, or taxable × rate) and
                compared to the recorded tax within tolerance. Verified matches close; discrepancies become
                exceptions with evidence — a human can review and override via the <code>X-User-Role</code> header.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 4. Agent */}
        <SectionTitle id="agent" icon={Bot}>5. Using the assistive agent</SectionTitle>
        <Card className="mt-3">
          <CardContent>
            <p className="text-sm text-gray-600">
              Use the floating <strong>ClosePilot Agent</strong> chat (bottom-right) to ask questions or run tasks. It operates
              under the same invariant the rest of the platform follows:
            </p>
            <p className="mt-2 flex items-center gap-2 text-sm text-gray-800">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              The agent can only <strong>propose</strong> and <strong>trigger</strong>; the PolicyEngine is always the final gate.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-md border border-gray-200 p-3">
                <p className="text-sm font-semibold text-gray-800">Ask (QUESTION)</p>
                <ul className="mt-1 list-inside text-xs text-gray-600">
                  <li>• &quot;What can I do here?&quot;</li>
                  <li>• &quot;How do I reconcile my transactions?&quot;</li>
                  <li>• &quot;What does evaluate policy do?&quot;</li>
                  <li>• &quot;Explain the risk on CASE_pay_821296_19&quot;</li>
                </ul>
              </div>
              <div className="rounded-md border border-gray-200 p-3">
                <p className="text-sm font-semibold text-gray-800">Command (TASK)</p>
                <ul className="mt-1 list-inside text-xs text-gray-600">
                  <li>• &quot;Handle all mismatched transactions&quot;</li>
                  <li>• &quot;Investigate all open exceptions&quot;</li>
                  <li>• &quot;Review every pending human-review case&quot;</li>
                </ul>
              </div>
            </div>
            <p className="mt-3 text-xs text-gray-500">
              Task results are safe: policy-eligible cases are auto-closed; everything else is <strong>staged for human
              review</strong> with an agent note and never forced. Progress streams as events you can inspect.
            </p>
          </CardContent>
        </Card>

        {/* 5. Policies */}
        <SectionTitle id="policies" icon={SlidersHorizontal}>6. Policy configuration</SectionTitle>
        <p className="text-sm text-gray-600">
          Open <strong>/policies</strong> to view and edit the live ruleset. Changes apply immediately to the next evaluation —
          no restart. Adjust <strong>thresholds</strong> (confidence, tolerance, high-impact amount, evidence count, match score)
          and <strong>rule toggles</strong> (e.g. allow medium/high-risk auto-close, enforce the multi-candidate or discrepancy
          gates). Add a change note; each save bumps the version and is written to the audit trail.
        </p>

        {/* 6. Audit & evidence */}
        <SectionTitle id="audit" icon={ScrollText}>7. Audit &amp; evidence</SectionTitle>
        <p className="text-sm text-gray-600">
          <strong>/audit</strong> is an append-only timeline: case creation, AI investigations, policy evaluations, human
          approvals/rejections, and agent actions (<code>AGENT_AUTO_CLOSED</code>, <code>AGENT_STAGED_FOR_REVIEW</code>,{" "}
          <code>POLICY_UPDATED</code>) are all recorded with actors, timestamps, and policy decisions.{" "}
          <strong>/evidence</strong> renders the provenance graph for a case, showing how records relate to one another.
        </p>

        {/* 7. Troubleshooting */}
        <SectionTitle id="troubleshoot" icon={HelpCircle}>8. Troubleshooting</SectionTitle>
        <Card className="mt-3">
          <CardContent>
            <p className="text-sm text-gray-600">
              If the backend is unreachable or returns a 5xx, a global error modal appears with the failing endpoint. Ensure the
              stack is running (<code>docker compose up -d</code>) and reachable, then retry. The AI (Groq) is optional — if the
              model isn&apos;t available, cases gracefully degrade to <strong>HUMAN_REVIEW</strong> rather than failing.
            </p>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
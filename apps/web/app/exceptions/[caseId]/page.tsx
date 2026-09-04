"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Modal } from "@/components/ui/modal";
import { api } from "@/lib/api";
import {
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Search,
} from "lucide-react";

interface CaseDetail {
  case_id: string;
  status: string;
  risk: string;
  match_score: number;
  outcome_type: string;
  amount: number;
  currency: string;
  related_record_ids: string[];
  candidate_matches: Array<{
    external_id: string;
    record_type: string;
    score: number;
    triggered: string[];
    signals: Record<string, unknown>;
  }>;
  discrepancy: { amount_diff: number; currency: string; detail?: string };
  deterministic_info: {
    rules_triggered: string[];
    candidate_ids: string[];
    signal_values: Record<string, unknown>;
    calculated_difference: number;
    tolerance_used: number;
    reason_codes: string[];
    match_score: number;
  };
  ai_proposal: {
    conclusion: string;
    root_cause?: string;
    confidence: number;
    risk_level: string;
    proposed_action: string;
    evidence_ids: string[];
    reason_codes: string[];
    unresolved_questions: string[];
  } | null;
  source: string;
  record_type: string;
  reviewer?: string;
  agent_note?: string;
}

interface PolicyDecision {
  allowed: boolean;
  decision: string;
  reason_codes: string[];
  required_role?: string;
  evidence_requirements: string[];
  policy_version: string;
}

interface InvestigationResult {
  case_id: string;
  proposal: CaseDetail["ai_proposal"];
  metadata: {
    model: string;
    latency_ms: number;
    validation_status: string;
    error?: string | null;
  };
  status: string;
}

interface InvestigationLogEntry {
  id: string;
  label: string;
  value?: string;
}

interface ModalState {
  open: boolean;
  variant: "info" | "error";
  title: string;
  entries: InvestigationLogEntry[];
}

const emptyModal: ModalState = { open: false, variant: "info", title: "", entries: [] };

export default function ExceptionInvestigator() {
  const params = useParams<{ caseId: string }>();
  const caseId = params.caseId;
  const [data, setData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [policy, setPolicy] = useState<PolicyDecision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Array<{ evidence_id: string; statement: string; source: string; entity_type: string; entity_id: string }>>([]);
  const [modal, setModal] = useState<ModalState>(emptyModal);

  const closeModal = () => setModal((m) => ({ ...m, open: false }));

  const buildModal = (v: Partial<ModalState>) =>
    setModal((m) => ({ ...m, ...v, open: true }));

  const loadCase = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<CaseDetail>(`/reconciliation/cases/${caseId}`);
      setData(res);
    } catch (e) {
      setError(String(e));
      buildModal({
        variant: "error",
        title: "Failed to load case",
        entries: [{ id: "error", label: "Error", value: String(e) }],
      });
    }
    setLoading(false);
  };

  const loadEvidence = async () => {
    try {
      const res = await api.get<{ evidence: Array<{ evidence_id: string; statement: string; source: string; entity_type: string; entity_id: string }> }>(`/cases/${caseId}/evidence`);
      setEvidence(res.evidence);
    } catch {
      // ignore
    }
  };

  const evaluatePolicy = async () => {
    try {
      const res = await api.post<PolicyDecision>(`/cases/${caseId}/policy`);
      setPolicy(res);
    } catch (e) {
      console.error(e);
      buildModal({
        variant: "error",
        title: "Policy evaluation failed",
        entries: [{ id: "error", label: "Error", value: String(e) }],
      });
    }
  };

  const investigate = async () => {
    setInvestigating(true);
    setError(null);
    try {
      const res = await api.post<InvestigationResult>(`/cases/${caseId}/investigate`);
      const meta = res?.metadata;
      if (meta && meta.validation_status !== "valid") {
        buildModal({
          variant: "error",
          title: "AI Investigation did not complete",
          entries: [
            { id: "status", label: "Status", value: meta.validation_status },
            { id: "model", label: "Model", value: meta.model || "-" },
            { id: "latency", label: "Latency", value: meta.latency_ms ? `${meta.latency_ms} ms` : "-" },
            { id: "error", label: "Error", value: meta.error || "No error details returned." },
          ],
        });
      } else if (meta?.model || meta?.latency_ms != null) {
        buildModal({
          variant: "info",
          title: "AI Investigation complete",
          entries: [
            { id: "status", label: "Status", value: meta?.validation_status ?? "valid" },
            { id: "model", label: "Model", value: meta?.model || "-" },
            { id: "latency", label: "Latency", value: meta?.latency_ms ? `${meta.latency_ms} ms` : "-" },
          ],
        });
      }
      await loadCase();
      setPolicy(null);
    } catch (e) {
      setError(String(e));
      buildModal({
        variant: "error",
        title: "AI Investigation failed",
        entries: [
          { id: "error", label: "Error", value: String(e) },
          { id: "action", label: "Action", value: "Please try again." },
        ],
      });
    }
    setInvestigating(false);
  };

  const approve = async () => {
    try {
      await api.post(`/cases/${caseId}/approve`);
      await loadCase();
    } catch (e) {
      setError(String(e));
      buildModal({
        variant: "error",
        title: "Approve action failed",
        entries: [{ id: "error", label: "Error", value: String(e) }],
      });
    }
  };

  const reject = async () => {
    try {
      await api.post(`/cases/${caseId}/reject`);
      await loadCase();
    } catch (e) {
      setError(String(e));
      buildModal({
        variant: "error",
        title: "Reject action failed",
        entries: [{ id: "error", label: "Error", value: String(e) }],
      });
    }
  };

  const keepException = async () => {
    try {
      await api.post(`/cases/${caseId}/keep-exception`);
      await loadCase();
    } catch (e) {
      setError(String(e));
      buildModal({
        variant: "error",
        title: "Keep-exception action failed",
        entries: [{ id: "error", label: "Error", value: String(e) }],
      });
    }
  };

  useEffect(() => {
    loadCase();
    loadEvidence();
  }, [caseId]);

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

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </DashboardLayout>
    );
  }

  if (error && !data) {
    return (
      <DashboardLayout>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <p className="font-medium text-red-700">Error loading case: {error}</p>
          <Link href="/exceptions">
            <Button variant="outline" size="sm" className="mt-2">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Exceptions
            </Button>
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  const canAutoClose = policy?.decision === "AUTO_CLOSE" && policy.allowed;
  const aiAvailable = !!data?.ai_proposal;

  return (
    <DashboardLayout>
      <div className="mb-6">
        <Link href="/exceptions" className="text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeft className="mr-1 inline h-3 w-3" /> Back to Exceptions
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{data?.case_id}</h1>
          {statusBadge(data?.status || "")}
          {riskBadge(data?.risk || "")}
        </div>
        <p className="mt-1 text-sm text-gray-500">
          {data?.record_type} · {data?.source} · {((data?.amount ?? 0) / 100).toLocaleString("en-IN", { style: "currency", currency: data?.currency || "INR" })}
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
          {error}
        </div>
      )}

      {data?.agent_note && (
        <div className="mb-4 rounded-lg border border-indigo-200 bg-indigo-50 p-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-500" />
            <p className="text-sm font-semibold text-indigo-800">
              {data.reviewer ? `Auto-reviewed by Agent (${data.reviewer})` : "Agent review"}
            </p>
          </div>
          <p className="mt-1 text-sm text-indigo-700">{data.agent_note}</p>
          <div className="mt-2">
            <p className="text-xs font-semibold text-indigo-600">Status</p>
            <p className="text-sm text-indigo-800">
              This case is <span className="font-semibold">HUMAN_REVIEW</span> — a person must decide.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Case Summary</CardTitle>
              <CardDescription>Overview of the reconciliation scenario</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div>
                  <p className="text-xs text-gray-500">Outcome</p>
                  <p className="font-medium">{data?.outcome_type || "-"}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Match Score</p>
                  <p className="font-medium">{data?.match_score?.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Discrepancy</p>
                  <p className="font-medium">
                    {data?.discrepancy
                      ? `${((data.discrepancy.amount_diff ?? 0) / 100).toLocaleString("en-IN", { style: "currency", currency: data.discrepancy.currency || "INR" })}`
                      : "None"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Tolerance Used</p>
                  <p className="font-medium">{data?.deterministic_info?.tolerance_used ?? 0} / 100</p>
                </div>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-sm font-semibold">Related Records</p>
                <div className="flex flex-wrap gap-2">
                  {(data?.related_record_ids ?? []).map((id) => (
                    <span key={id} className="rounded border bg-gray-50 px-2 py-1 font-mono text-xs">
                      {id}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-sm font-semibold">Deterministic Signals</p>
                <div className="flex flex-wrap gap-2">
                  {(data?.deterministic_info?.rules_triggered ?? []).map((rule) => (
                    <Badge key={rule} variant="secondary">
                      {rule}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-sm font-semibold">Reason Codes</p>
                <div className="flex flex-wrap gap-2">
                  {(data?.deterministic_info?.reason_codes ?? []).map((rc) => (
                    <span key={rc} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600">
                      {rc}
                    </span>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {data?.candidate_matches && data.candidate_matches.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Candidate Matches</CardTitle>
                <CardDescription>Identified by the reconciliation engine</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.candidate_matches.map((c) => (
                    <div key={c.external_id} className="flex items-center justify-between rounded-md border p-3">
                      <div>
                        <p className="font-mono text-sm font-medium">{c.external_id}</p>
                        <p className="text-xs text-gray-500">
                          {c.record_type} · score {c.score.toFixed(1)} · signals: {c.triggered.join(", ")}
                        </p>
                      </div>
                      <Badge variant={c.score >= 100 ? "success" : c.score >= 60 ? "warning" : "secondary"}>
                        {c.score.toFixed(0)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-indigo-500" />
                  AI Investigation
                </CardTitle>
                <CardDescription>The LLM proposes, policy authorizes</CardDescription>
              </div>
              <Button size="sm" onClick={investigate} disabled={investigating}>
                <Search className="mr-1 h-4 w-4" />
                {investigating ? "Investigating..." : "Investigate"}
              </Button>
            </CardHeader>
            <CardContent>
              {!aiAvailable && !investigating && (
                <p className="text-sm text-gray-400">
                  No AI investigation yet. Click &quot;Investigate&quot; to run the AI investigator with read-only tools.
                </p>
              )}
              {aiAvailable && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">{data?.ai_proposal?.conclusion}</Badge>
                    <Badge variant={data?.ai_proposal?.risk_level === "LOW" ? "success" : "destructive"}>
                      {data?.ai_proposal?.risk_level} risk
                    </Badge>
                    <span className="text-sm font-medium">
                      Confidence: {((data?.ai_proposal?.confidence ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  {data?.ai_proposal?.root_cause && (
                    <div>
                      <p className="text-xs font-semibold text-gray-500">Root Cause</p>
                      <p className="text-sm">{data.ai_proposal.root_cause}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs font-semibold text-gray-500">Proposed Action</p>
                    <p className="text-sm font-medium">{data?.ai_proposal?.proposed_action}</p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-semibold text-gray-500">Reason Codes</p>
                    <div className="flex flex-wrap gap-1">
                      {(data?.ai_proposal?.reason_codes ?? []).map((rc) => (
                        <Badge key={rc} variant="outline">
                          {rc}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-semibold text-gray-500">Evidence IDs Cited</p>
                    <div className="flex flex-wrap gap-1">
                      {(data?.ai_proposal?.evidence_ids ?? []).map((id) => (
                        <span key={id} className="rounded border bg-gray-50 px-2 py-1 font-mono text-xs">
                          {id}
                        </span>
                      ))}
                    </div>
                  </div>
                  {(data?.ai_proposal?.unresolved_questions?.length ?? 0) > 0 && (
                    <div>
                      <p className="mb-1 text-xs font-semibold text-gray-500">Unresolved Questions</p>
                      <ul className="list-disc pl-5 text-sm">
                        {data?.ai_proposal?.unresolved_questions.map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Evidence
              </CardTitle>
            </CardHeader>
            <CardContent>
              {evidence.length === 0 && (
                <p className="text-sm text-gray-400">No evidence items recorded for this case yet.</p>
              )}
              <div className="space-y-2">
                {evidence.map((e) => (
                  <div key={e.evidence_id} className="rounded-md border p-3">
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">{e.source}</Badge>
                      <span className="font-mono text-xs text-gray-400">{e.evidence_id}</span>
                    </div>
                    <p className="mt-2 text-sm">{e.statement}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Policy Decision</CardTitle>
              <CardDescription>Deterministic authorization</CardDescription>
            </CardHeader>
            <CardContent>
              {!policy && (
                <Button size="sm" variant="outline" onClick={evaluatePolicy} className="w-full">
                  Evaluate Policy
                </Button>
              )}
              {policy && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant={policy.allowed ? "success" : "destructive"}>
                      {policy.decision}
                    </Badge>
                    {policy.required_role && (
                      <span className="text-xs text-gray-500">Role: {policy.required_role}</span>
                    )}
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-semibold text-gray-500">Reasons</p>
                    <div className="flex flex-wrap gap-1">
                      {policy.reason_codes.map((rc) => (
                        <Badge key={rc} variant="outline">
                          {rc}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-gray-400">Policy version {policy.policy_version}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
              <CardDescription>Operational decisions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Button
                  variant="success"
                  className="w-full"
                  onClick={approve}
                  disabled={!canAutoClose && data?.status !== "HUMAN_REVIEW"}
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Approve & Close
                </Button>
                <Button variant="outline" className="w-full" onClick={keepException}>
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  Keep Exception
                </Button>
                <Button variant="destructive" className="w-full" onClick={reject}>
                  <XCircle className="mr-2 h-4 w-4" />
                  Reject Proposal
                </Button>
                {!canAutoClose && (
                  <p className="text-xs text-gray-400">
                    Policy does not currently authorize auto-close. Evaluate policy or run investigation first.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Evidence Graph</CardTitle>
            </CardHeader>
            <CardContent>
              <Link href={`/evidence?case=${caseId}`}>
                <Button variant="outline" size="sm" className="w-full">
                  View Evidence Graph
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>

      <Modal
        open={modal.open}
        onClose={closeModal}
        variant={modal.variant}
        title={modal.title}
      >
        <dl className="space-y-3">
          {modal.entries.map((entry) => (
            <div key={entry.id}>
              <dt className="text-xs font-semibold text-gray-500">{entry.label}</dt>
              <dd className="mt-0.5 font-mono text-xs break-words whitespace-pre-wrap">{entry.value || "-"}</dd>
            </div>
          ))}
        </dl>
      </Modal>
    </DashboardLayout>
  );
}

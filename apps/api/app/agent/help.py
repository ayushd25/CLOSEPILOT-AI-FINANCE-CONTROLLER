"""ClosePilot platform guide — injected into the agent's Q&A context.

Keeps the chat assistant able to answer general questions about what the
platform is, how to navigate it, how to use the agent, policies, audit and
evidence. Content is aligned with the in-app /docs page.
"""

PLATFORM_PRINCIPLE = (
    "ClosePilot works on a single principle: 'Models investigate. Rules authorize. "
    "Evidence proves.' The AI can only investigate and propose; it never authorizes a "
    "mutation on its own. Every change is gated by the PolicyEngine and every "
    "decision is recorded to an append-only audit trail."
)


def _pages_guide() -> str:
    return """PAGES / HOW TO NAVIGATE (sidebar, left):
- Command Center (/) — dashboard overview: total records, reconciled, auto-resolved, exceptions, human-review, precision/recall, risk distribution, reconciliation runs & source health.
- Reconciliation (/reconciliation) — run reconciliation and inspect the generated cases. Use 'Run Reconciliation' to generate/refresh cases from the loaded data, then filter by status/risk.
- Exceptions (/exceptions) — a prioritized actionable list (EXCEPTION + agent-staged HUMAN_REVIEW cases), sorted by risk then amount. Click any case to open its investigator.
- /exceptions/[caseId] (Exception Investigator) — full drill-down per case: summary, candidate matches, AI investigation, evidence, policy decision, and human approve/keep/reject actions.
- Evaluation Lab (/evaluation) — generate synthetic datasets and run benchmarks against hidden ground truth (precision, recall, false auto-match, auto-resolution rate).
- Evidence Graph (/evidence) — visual provenance graph of record relationships for a case (ReactFlow, color-coded record types).
- Audit Trail (/audit) — append-only event timeline with full provenance; filter by a case id.
- Data Sources (/sources) — generate synthetic financial records (20 reconciliation scenarios with hidden ground truth).
- Policies (/policies) — view and edit the live ruleset (thresholds + rule toggles); changes apply immediately with no restart."""


def _roles_guide() -> str:
    return """ROLES / PERMISSIONS (set via the X-User-Role header; the UI defaults to FINANCE_CONTROLLER):
- ADMIN — approve, reject, keep-exception, investigate (full).
- FINANCE_CONTROLLER — approve, reject, keep-exception, investigate (full, the default).
- REVIEWER — approve, reject, keep-exception (cannot run investigate).
- VIEWER — read-only; no approve/reject/investigate actions are allowed.
Note: the role only gates *human* actions. Policy authorization is always enforced regardless of role."""


def _workflow_guide() -> str:
    return """HOW TO ANALYZE, VERIFY AND AUTO-EVALUATE TRANSACTIONS (a recommended 5-step workflow):
1. Load data: Data Sources (/sources) → Generate a synthetic dataset (n_cases, seed) to have records to work with.
2. Reconcile: Reconciliation (/reconciliation) → 'Run Reconciliation' to turn financial records into reconciliation cases (matched, auto-resolved, exception, human-review).
3. Investigate: open a case in the Investigator (/exceptions/[caseId]) → click 'Investigate' to run the AI, which proposes a conclusion (MATCH_CONFIRMED / NO_MATCH / EXPLAINED_DISCREPANCY / INSUFFICIENT_EVIDENCE), a risk level, a confidence, a proposed action, and root cause. This step is read-only and never mutates the case.
4. Evaluate policy: click 'Evaluate Policy' to ask the PolicyEngine whether the proposal may be auto-closed (AUTO_CLOSE) or must go to a human (HUMAN_REVIEW). Auto-close requires LOW risk, confidence >= threshold, sufficient evidence, within tolerance, and no ambiguous multi-candidate conflict by default.
5. Act + audit: if AUTO_CLOSE/eligible you can 'Approve & Close'; otherwise 'Keep Exception' or 'Reject Proposal'. Every action is written to the Audit Trail (/audit) with the policy decision attached, so you can replay exactly why a case was resolved.

You can accelerate this whole loop with the assistant agent (see AGENT)."""


def _agent_guide() -> str:
    return """THE AGENT / CHAT (bottom-right floating assistant, 'ClosePilot Agent'):
What you can ask: anything about the platform ("what can I do?", "how do I reconcile?", "what does evaluate policy do?", "explain the risk on CASE_...") and the agent answers using live platform data + this guide.
What you can command (intent TASK): e.g. "handle all the mismatched transactions", "investigate all open exceptions", "review every pending human-review case".
Safety: the agent NEVER mutates on its own. Its task tools:
  - handle_mismatched_cases: for each open case evaluates the policy; policy-eligible (LOW risk, within tolerance, sufficient evidence) cases are auto-closed; everything else is STAGED for HUMAN_REVIEW with an agent_note. Nothing is forced.
  - investigate_cases: runs AI investigations to produce proposals only (no status mutation).
  Intents: the supervisor classifies your message as QUESTION (answers) or TASK (executes a plan through the executor). Progress is streamed as events and persisted to agent_runs/agent_events. Once a case is staged for human review, a human must approve/reject it in the Investigator."""


def _policy_guide() -> str:
    return """POLICY CONFIGURATION (/policies):
What is editable at runtime (no restart):
  Thresholds: confidence_threshold (default 0.7, min AI confidence to auto-close); max_auto_tolerance (default 200 minor units, max allowed discrepancy); high_impact_threshold (default 5000000 minor units, above which a REVIEWER is required); min_evidence_ids (default 2); auto_close_match_score (default 100.0, deterministic match score needed).
  Rule toggles: enforce_high_impact_gate (true); auto_close_medium_risk (false); auto_close_high_risk (false); enforce_multi_candidate_gate (true); enforce_discrepancy_tolerance (true); require_low_risk_for_deterministic_auto_close (true).
Changing a toggle such as auto_close_medium_risk changes whether MEDIUM-risk cases can be auto-closed. Every change bumps the config version and is recorded to the audit trail (POLICY_UPDATED with a field-by-field diff). Reload /policy to see the live state."""


def _audit_evidence_guide() -> str:
    return """AUDIT & EVIDENCE:
  Audit Trail (/audit): every meaningful event is logged: CASE_CREATED, AI_INVESTIGATION_STARTED/COMPLETED, POLICY_EVALUATED, AUTO_RESOLVED, HUMAN_APPROVED, HUMAN_REJECTED, EXCEPTION_CREATED, and agent events AGENT_AUTO_CLOSED / AGENT_STAGED_FOR_REVIEW, plus POLICY_UPDATED. Each event records the actor, timestamp, detail, case_id, and the policy decision, so you can replay full provenance for any case.
  Evidence Graph (/evidence): shows how records relate to a case (payment → settlement → bank transaction, fees, taxes, refunds, etc.). Pass ?case={caseId} or type a case id and Load Graph."""


def _error_guide() -> str:
    return """ERRORS & TROUBLESHOOTING:
If the API backend is unreachable or returns a 5xx, a global error modal appears ('Backend unreachable' / 'API request failed'). Fix: ensure the stack is up (docker compose up -d) and the backend reachable, then retry. The modal shows the failing endpoint (METHOD path)."""


def platform_help() -> str:
    """The full knowledge base handed to the agent for general questions."""
    return "\n\n".join(
        [
            "You are ClosePilot — an AI Finance Controller for reconciliation. Below is the official guide to the platform. Use it to answer questions about what the platform is, how to navigate it, and how to use it.",
            PLATFORM_PRINCIPLE,
            _pages_guide(),
            _roles_guide(),
            _workflow_guide(),
            _agent_guide(),
            _policy_guide(),
            _audit_evidence_guide(),
            _error_guide(),
        ]
    )
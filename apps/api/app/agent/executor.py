from typing import Any, Optional

from app.db import Database
from app.domain.agent import AgentEvent, AgentEventType, AgentRun
from app.domain.cases import CaseStatus, ReconciliationCase
from app.policy.engine import PolicyEngine
from app.reconciliation.repositories import ReconciliationCaseRepository


class AgentToolError(Exception):
    pass


class AgentExecutor:
    """Read-only tools + authorised action executors.

    Enforces ClosePilot's core invariant: the agent (LLM) can only *propose*
    and *trigger*; every state mutation is gated by the PolicyEngine and
    recorded to the audit trail. Operations that are not policy-eligible are
    staged for HUMAN_REVIEW and are never forced through.
    """

    def __init__(self, session_id: str = "agent", role: str = "FINANCE_CONTROLLER", agent_tool_name: str = "assistant"):
        self.db = Database.get_db()
        self.case_repo = ReconciliationCaseRepository(self.db)
        self.policy = PolicyEngine()._with_repo()
        self.session_id = session_id
        self.role = role
        self.agent_tool_name = agent_tool_name

    # ------------------------------------------------------------------ #
    # Read-only tools                                                    #
    # ------------------------------------------------------------------ #
    async def summary(self, args: dict[str, Any] | None = None) -> dict:
        db = self.db
        total_records = await db.financial_records.count_documents({})
        total_cases = await db.reconciliation_cases.count_documents({})
        resolved = await db.reconciliation_cases.count_documents(
            {"status": {"$in": ["AUTO_RESOLVED", "RESOLVED", "MATCHED"]}}
        )
        auto_resolved = await db.reconciliation_cases.count_documents({"status": "AUTO_RESOLVED"})
        human_review = await db.reconciliation_cases.count_documents({"status": "HUMAN_REVIEW"})
        exceptions = await db.reconciliation_cases.count_documents({"status": "EXCEPTION"})
        unmatched = await db.reconciliation_cases.count_documents({"status": "UNPROCESSED"})
        open_exceptions = await db.reconciliation_cases.count_documents(
            {"status": {"$in": ["UNPROCESSED", "EXCEPTION", "HUMAN_REVIEW"]}}
        )
        return {
            "total_records": total_records,
            "total_cases": total_cases,
            "resolved": resolved,
            "auto_resolved": auto_resolved,
            "human_review": human_review,
            "exceptions": exceptions,
            "unmatched": unmatched,
            "open_cases": open_exceptions,
        }

    async def list_cases(self, args: dict[str, Any] | None = None) -> dict:
        args = args or {}
        status = args.get("status")
        risk = args.get("risk")
        limit = int(args.get("limit", 25))
        cases, total = await self.case_repo.list_cases(status=status, risk=risk, limit=limit, skip=0)
        return {
            "total": total,
            "cases": [
                {
                    "case_id": c.case_id,
                    "status": c.status.value,
                    "outcome_type": c.outcome_type,
                    "risk": c.risk.value,
                    "amount": c.amount,
                    "currency": c.currency,
                    "record_type": c.record_type,
                }
                for c in cases
            ],
        }

    async def get_case(self, args: dict[str, Any] | None = None) -> dict:
        args = args or {}
        case_id = args.get("case_id")
        case = await self.case_repo.get(case_id) if case_id else None
        if not case:
            raise AgentToolError(f"case not found: {case_id}")
        return case.to_mongo()

    async def list_runs(self, args: dict[str, Any] | None = None) -> dict:
        cursor = self.db.reconciliation_runs.find({}).sort("started_at", -1).limit(
            int((args or {}).get("limit", 10))
        )
        runs = await cursor.to_list(length=10)
        return {
            "runs": [
                {
                    "run_id": str(r.get("_id")),
                    "started_at": r.get("started_at"),
                    "total_records": r.get("total_records"),
                    "matched": r.get("matched"),
                    "exceptions": r.get("exceptions"),
                    "auto_resolved": r.get("auto_resolved"),
                }
                for r in runs
            ]
        }

    # ------------------------------------------------------------------ #
    # Authorised action executors                                        #
    # ------------------------------------------------------------------ #
    async def handle_mismatched_cases(self, args: dict[str, Any] | None = None) -> dict:
        """Auto-resolve every policy-eligible open case; stage the rest.

        This is the "handle all mismatched transactions" executor. It only
        triggers actions the PolicyEngine permits (LOW risk, concise to the
        rules); anything else is marked HUMAN_REVIEW for a person, and is
        never mutated further.
        """
        args = args or {}
        targets = self._target_case_ids(args)
        executed: list[str] = []
        staged: list[str] = []
        denied: list[str] = []
        processed = 0

        for case in await self._load_targets(targets):
            processed += 1
            if case.status in (CaseStatus.RESOLVED, CaseStatus.AUTO_RESOLVED, CaseStatus.REJECTED):
                continue
            decision = await self.policy.evaluate(case, case.ai_proposal)
            if decision.allowed and decision.decision == "AUTO_CLOSE":
                await self._auto_close(case, decision)
                executed.append(case.case_id)
            else:
                await self._stage_for_review(case, decision)
                staged.append(case.case_id)

        return {
            "processed": processed,
            "executed": executed,
            "staged_for_human_review": staged,
            "denied": denied,
        }

    async def investigate_cases(self, args: dict[str, Any] | None = None) -> dict:
        """Run an AI investigation on each open target case (read-only + proposal)."""
        from app.ai.service import AIInvestigatorService

        args = args or {}
        service = AIInvestigatorService()
        targets = self._target_case_ids(args)
        investigated = 0
        degraded: list[str] = []
        for case_id in targets[: int(args.get("limit", 50))]:
            proposal, metadata = await service.investigate(case_id)
            if proposal is not None:
                await self._persist_proposal(case_id, proposal)
                investigated += 1
            else:
                degraded.append(case_id)
        return {"investigated": investigated, "degraded_to_review": degraded}

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #
    def _target_case_ids(self, args: dict[str, Any] | None = None) -> list[str]:
        args = args or {}
        explicit = args.get("case_ids")
        if explicit:
            return [str(c) for c in explicit]
        return []

    async def _load_targets(self, case_ids: Optional[list[str]] = None) -> list[ReconciliationCase]:
        if case_ids:
            out = []
            for cid in case_ids:
                case = await self.case_repo.get(cid)
                if case:
                    out.append(case)
            return out
        cursor = self.db.reconciliation_cases.find(
            {"status": {"$in": ["UNPROCESSED", "EXCEPTION", "HUMAN_REVIEW"]}}
        ).limit(500)
        docs = await cursor.to_list(length=500)
        return [ReconciliationCase.from_mongo(d) for d in docs]

    async def _auto_close(self, case: ReconciliationCase, decision) -> None:
        before = {"status": case.status.value}
        case.status = CaseStatus.AUTO_RESOLVED
        case.final_action = "agent_auto_close"
        case.reviewer = self.agent_tool_name
        await self.case_repo.update(case)
        from app.audit.service import AuditService

        await AuditService().record(
            event_type="AGENT_AUTO_CLOSED",
            case_id=case.case_id,
            actor_type="agent",
            actor_id=self.agent_tool_name,
            before_state=before,
            after_state={"status": case.status.value},
            policy_decision=decision.model_dump(),
            correlation_id=self.session_id,
            detail=f"Agent auto-closed policy-eligible case (session {self.session_id})",
        )

    async def _stage_for_review(self, case: ReconciliationCase, decision) -> None:
        before = {"status": case.status.value}
        case.status = CaseStatus.HUMAN_REVIEW
        case.final_action = "pending_human_review"
        case.reviewer = self.agent_tool_name
        awaits_reason = "; ".join(decision.reason_codes or ["policy_not_authorized"]) if isinstance(decision.reason_codes, list) else "policy_not_authorized"
        note = (
            f"Auto-reviewed by Agent (session {self.session_id}) and staged for a human: "
            f"policy did not authorize auto-close ({awaits_reason}). No mutation was forced."
        )
        await self.case_repo.update(case)
        await self.db.reconciliation_cases.update_one(
            {"case_id": case.case_id},
            {"$set": {"agent_note": note}},
        )
        from app.audit.service import AuditService

        await AuditService().record(
            event_type="AGENT_STAGED_FOR_REVIEW",
            case_id=case.case_id,
            actor_type="agent",
            actor_id=self.agent_tool_name,
            before_state=before,
            after_state={"status": case.status.value, "final_action": "pending_human_review"},
            policy_decision=decision.model_dump(),
            correlation_id=self.session_id,
            detail=note,
        )

    async def _persist_proposal(self, case_id: str, proposal) -> None:
        doc = proposal.model_dump() if hasattr(proposal, "model_dump") else dict(proposal)
        await self.db.reconciliation_cases.update_one(
            {"case_id": case_id},
            {"$set": {"ai_proposal": doc}},
        )


TOOL_REGISTRY: dict[str, str] = {
    "summary": "Read-only platform summary (record/case counts).",
    "list_cases": "Read-only. List reconciliation cases. Args: status (optional), risk (optional), limit (default 25).",
    "get_case": "Read-only. Get a single case by case_id.",
    "list_runs": "Read-only. List recent reconciliation runs.",
    "handle_mismatched_cases": "AUTHORISED ACTION. Auto-resolve policy-eligible open cases; stage the rest for human review. Args: case_ids (optional list) or status. Safe: only policy-eligible cases mutate.",
    "investigate_cases": "AUTHORISED ACTION. Run AI investigation on open cases (proposes only). Args: case_ids or limit.",
}


def get_tool_help() -> str:
    return "\n".join(f"- {name}: {description}" for name, description in TOOL_REGISTRY.items())
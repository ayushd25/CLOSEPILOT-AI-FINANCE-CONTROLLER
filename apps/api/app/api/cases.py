from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.ai.service import AIInvestigatorService
from app.audit.service import AuditService
from app.db import Database
from app.domain.cases import AIProposal, CaseStatus, RiskLevel
from app.policy.engine import PolicyEngine
from app.reconciliation.repositories import ReconciliationCaseRepository
from app.security.auth import get_user_role

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/{case_id}/investigate")
async def investigate_case(case_id: str):
    service = AIInvestigatorService()
    proposal, metadata = await service.investigate(case_id)

    db = Database.get_db()
    audit = AuditService()

    case_doc = await db.reconciliation_cases.find_one({"case_id": case_id})
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    await audit.record(
        event_type="AI_INVESTIGATION_STARTED",
        case_id=case_id,
        actor_type="system",
        detail="AI investigation started",
    )

    if proposal is None:
        await audit.record(
            event_type="AI_INVESTIGATION_COMPLETED",
            case_id=case_id,
            actor_type="system",
            detail=f"AI investigation failed: {metadata.error or 'unavailable'}",
            model_metadata=metadata.model_dump(),
        )
        case_doc["status"] = CaseStatus.HUMAN_REVIEW.value
        case_doc["ai_proposal"] = None
        await db.reconciliation_cases.update_one(
            {"case_id": case_id},
            {"$set": {"status": CaseStatus.HUMAN_REVIEW.value, "ai_proposal": None}},
        )
        return {
            "case_id": case_id,
            "proposal": None,
            "metadata": metadata.model_dump(),
            "status": "HUMAN_REVIEW",
        }

    ai_proposal = AIProposal(
        case_id=case_id,
        conclusion=proposal.conclusion,
        root_cause=proposal.root_cause,
        confidence=proposal.confidence,
        risk_level=proposal.risk_level,
        proposed_action=proposal.proposed_action,
        evidence_ids=proposal.evidence_ids,
        reason_codes=proposal.reason_codes,
        unresolved_questions=proposal.unresolved_questions,
    )

    await db.reconciliation_cases.update_one(
        {"case_id": case_id},
        {"$set": {"ai_proposal": ai_proposal.model_dump()}},
    )

    await audit.record(
        event_type="AI_INVESTIGATION_COMPLETED",
        case_id=case_id,
        actor_type="system",
        detail=f"AI investigation completed: {proposal.conclusion} confidence={proposal.confidence:.2f}",
        model_metadata=metadata.model_dump(),
    )

    return {
        "case_id": case_id,
        "proposal": ai_proposal.model_dump(),
        "metadata": metadata.model_dump(),
    }


@router.get("/{case_id}/investigation")
async def get_investigation(case_id: str):
    db = Database.get_db()
    case_doc = await db.reconciliation_cases.find_one({"case_id": case_id})
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case_doc.get("ai_proposal")


@router.post("/{case_id}/approve")
async def approve_case(case_id: str, user_role: str = Depends(get_user_role)):
    db = Database.get_db()
    audit = AuditService()
    policy = PolicyEngine()

    case_doc = await db.reconciliation_cases.find_one({"case_id": case_id})
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    from app.domain.cases import ReconciliationCase

    case = ReconciliationCase.from_mongo(case_doc)
    policy_decision = policy.evaluate_human_action(case, "approve", user_role)
    if not policy_decision.allowed:
        raise HTTPException(status_code=403, detail={
            "error": "Not authorized",
            "reason": policy_decision.reason_codes,
        })

    before = {"status": case.status.value}
    case.status = CaseStatus.RESOLVED
    case.final_action = "human_approve"
    case.reviewer = user_role
    await db.reconciliation_cases.update_one(
        {"case_id": case_id},
        {"$set": {
            "status": CaseStatus.RESOLVED.value,
            "final_action": "human_approve",
            "reviewer": user_role,
        }},
    )
    await audit.record(
        event_type="HUMAN_APPROVED",
        case_id=case_id,
        actor_type="human",
        actor_id=user_role,
        before_state=before,
        after_state={"status": CaseStatus.RESOLVED.value},
        policy_decision=policy_decision.model_dump(),
    )
    return {"case_id": case_id, "status": CaseStatus.RESOLVED.value, "policy": policy_decision.model_dump()}


@router.post("/{case_id}/reject")
async def reject_case(case_id: str, user_role: str = Depends(get_user_role)):
    db = Database.get_db()
    audit = AuditService()
    policy = PolicyEngine()

    case_doc = await db.reconciliation_cases.find_one({"case_id": case_id})
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    from app.domain.cases import ReconciliationCase

    case = ReconciliationCase.from_mongo(case_doc)
    policy_decision = policy.evaluate_human_action(case, "reject", user_role)
    if not policy_decision.allowed:
        raise HTTPException(status_code=403, detail="Not authorized")

    before = {"status": case.status.value}
    case.status = CaseStatus.REJECTED
    case.final_action = "human_reject"
    case.reviewer = user_role
    await db.reconciliation_cases.update_one(
        {"case_id": case_id},
        {"$set": {
            "status": CaseStatus.REJECTED.value,
            "final_action": "human_reject",
            "reviewer": user_role,
        }},
    )
    await audit.record(
        event_type="HUMAN_REJECTED",
        case_id=case_id,
        actor_type="human",
        actor_id=user_role,
        before_state=before,
        after_state={"status": CaseStatus.REJECTED.value},
        policy_decision=policy_decision.model_dump(),
    )
    return {"case_id": case_id, "status": CaseStatus.REJECTED.value}


@router.post("/{case_id}/keep-exception")
async def keep_exception(case_id: str, user_role: str = Depends(get_user_role)):
    db = Database.get_db()
    audit = AuditService()
    policy = PolicyEngine()

    case_doc = await db.reconciliation_cases.find_one({"case_id": case_id})
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    from app.domain.cases import ReconciliationCase

    case = ReconciliationCase.from_mongo(case_doc)
    policy_decision = policy.evaluate_human_action(case, "keep-exception", user_role)
    if not policy_decision.allowed:
        raise HTTPException(status_code=403, detail="Not authorized")

    before = {"status": case.status.value}
    case.status = CaseStatus.EXCEPTION
    case.final_action = "keep_exception"
    case.reviewer = user_role
    await db.reconciliation_cases.update_one(
        {"case_id": case_id},
        {"$set": {
            "status": CaseStatus.EXCEPTION.value,
            "final_action": "keep_exception",
            "reviewer": user_role,
        }},
    )
    await audit.record(
        event_type="EXCEPTION_CREATED",
        case_id=case_id,
        actor_type="human",
        actor_id=user_role,
        before_state=before,
        after_state={"status": CaseStatus.EXCEPTION.value},
        policy_decision=policy_decision.model_dump(),
    )
    return {"case_id": case_id, "status": CaseStatus.EXCEPTION.value}


@router.post("/{case_id}/policy")
async def evaluate_policy(case_id: str):
    db = Database.get_db()
    policy = PolicyEngine()

    case_doc = await db.reconciliation_cases.find_one({"case_id": case_id})
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    from app.domain.cases import ReconciliationCase

    case = ReconciliationCase.from_mongo(case_doc)
    proposal = case.ai_proposal

    if case.discrepancy and case.discrepancy.amount_diff:
        pass

    decision = await policy._with_repo().evaluate(case, proposal)
    return decision.model_dump()


@router.get("/{case_id}/evidence")
async def get_case_evidence(case_id: str):
    from app.reconciliation.repositories import ReconciliationCaseRepository
    from app.evidence.service import EvidenceService

    repo = ReconciliationCaseRepository()
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    evidence_service = EvidenceService()
    evidence = await evidence_service.get_evidence_for_case(case_id)
    return {"evidence": [e.to_mongo() for e in evidence]}


@router.get("/{case_id}/graph")
async def get_case_graph(case_id: str):
    from app.reconciliation.repositories import ReconciliationCaseRepository
    from app.evidence.service import EvidenceService

    repo = ReconciliationCaseRepository()
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    evidence_service = EvidenceService()
    graph = await evidence_service.get_graph(case)
    return graph.model_dump()

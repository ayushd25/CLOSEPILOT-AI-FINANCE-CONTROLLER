import pytest

from app.policy.engine import PolicyEngine
from app.domain.cases import (
    AIProposal,
    CaseStatus,
    DeterministicInfo,
    Discrepancy,
    PolicyDecision,
    ReconciliationCase,
    RiskLevel,
)


def _case(risk=RiskLevel.LOW, score=100, amount=10000, discrepancy=0, candidates=None):
    return ReconciliationCase(
        case_id="CASE_1",
        status=CaseStatus.AUTO_RESOLVED,
        match_score=score,
        risk=risk,
        amount=amount,
        discrepancy=Discrepancy(amount_diff=discrepancy, currency="INR"),
        deterministic_info=DeterministicInfo(
            match_score=score,
            candidate_ids=candidates or [],
            reason_codes=["test"],
        ),
    )


def test_low_risk_high_score_auto_close():
    policy = PolicyEngine()
    case = _case(risk=RiskLevel.LOW, score=120)
    decision = policy.evaluate(case)
    assert decision.decision == "AUTO_CLOSE"
    assert decision.allowed is True


def test_high_risk_requires_human():
    policy = PolicyEngine()
    case = _case(risk=RiskLevel.HIGH, score=120)
    decision = policy.evaluate(case)
    assert decision.decision == "HUMAN_REVIEW"
    assert decision.allowed is False


def test_high_impact_requires_reviewer():
    policy = PolicyEngine()
    case = _case(risk=RiskLevel.LOW, score=120, amount=100_00_000)
    decision = policy.evaluate(case)
    assert decision.required_role == "REVIEWER"
    assert decision.allowed is False


def test_ai_insufficient_evidence_keeps_exception():
    policy = PolicyEngine()
    case = _case(risk=RiskLevel.LOW, score=80)
    proposal = AIProposal(
        case_id="CASE_1",
        conclusion="INSUFFICIENT_EVIDENCE",
        confidence=0.1,
        risk_level=RiskLevel.HIGH,
        proposed_action="KEEP_EXCEPTION",
        evidence_ids=[],
    )
    decision = policy.evaluate(case, proposal)
    assert decision.decision == "KEEP_EXCEPTION"
    assert decision.allowed is False


def test_ai_low_confidence_escalates():
    policy = PolicyEngine()
    case = _case(risk=RiskLevel.LOW, score=70)
    proposal = AIProposal(
        case_id="CASE_1",
        conclusion="MATCH_CONFIRMED",
        confidence=0.4,
        risk_level=RiskLevel.MEDIUM,
        proposed_action="AUTO_CLOSE",
        evidence_ids=["ev1", "ev2"],
    )
    decision = policy.evaluate(case, proposal)
    assert decision.decision == "HUMAN_REVIEW"
    assert decision.allowed is False


def test_ai_valid_proposal_auto_closes():
    policy = PolicyEngine()
    case = _case(risk=RiskLevel.LOW, score=60, discrepancy=0)
    proposal = AIProposal(
        case_id="CASE_1",
        conclusion="EXPLAINED_DISCREPANCY",
        confidence=0.9,
        risk_level=RiskLevel.LOW,
        proposed_action="AUTO_CLOSE",
        evidence_ids=["ev1", "ev2"],
        reason_codes=["fee_explains"],
    )
    decision = policy.evaluate(case, proposal)
    assert decision.decision == "AUTO_CLOSE"
    assert decision.allowed is True


def test_human_approve_allowed_for_reviewer():
    policy = PolicyEngine()
    case = _case()
    decision = policy.evaluate_human_action(case, "approve", "REVIEWER")
    assert decision.allowed is True


def test_viewer_cannot_approve():
    policy = PolicyEngine()
    case = _case()
    decision = policy.evaluate_human_action(case, "approve", "VIEWER")
    assert decision.allowed is False

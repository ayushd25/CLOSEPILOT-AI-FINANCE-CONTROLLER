import pytest

from app.ai.proposals import InvestigationProposal, RiskLevel


def test_valid_proposal():
    p = InvestigationProposal(
        case_id="CASE_1",
        conclusion="MATCH_CONFIRMED",
        confidence=0.9,
        risk_level=RiskLevel.LOW,
        proposed_action="AUTO_CLOSE",
        evidence_ids=["ev1"],
    )
    assert p.validate_evidence_requirement()


def test_invalid_proposal_missing_case_id():
    with pytest.raises(Exception):
        InvestigationProposal(
            conclusion="MATCH_CONFIRMED",
            confidence=0.9,
        )


def test_insufficient_evidence_fails_validation():
    p = InvestigationProposal(
        case_id="CASE_1",
        conclusion="MATCH_CONFIRMED",
        confidence=0.9,
        risk_level=RiskLevel.LOW,
        proposed_action="AUTO_CLOSE",
        evidence_ids=[],
    )
    assert not p.validate_evidence_requirement()

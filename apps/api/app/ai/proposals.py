from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.domain.cases import RiskLevel


class InvestigationProposal(BaseModel):
    case_id: str
    conclusion: str = Field(description="INSUFFICIENT_EVIDENCE | MATCH_CONFIRMED | NO_MATCH | EXPLAINED_DISCREPANCY")
    root_cause: Optional[str] = Field(default=None, description="Likely root cause of discrepancy")
    confidence: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0")
    risk_level: RiskLevel = Field(default=RiskLevel.HIGH)
    proposed_action: str = Field(description="AUTO_CLOSE | KEEP_EXCEPTION | MATCH | RESOLVE | REJECT")
    evidence_ids: list[str] = Field(default_factory=list, description="Evidence IDs that support the conclusion")
    reason_codes: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

    def validate_evidence_requirement(self) -> bool:
        return len(self.evidence_ids) > 0


class InvestigationMetadata(BaseModel):
    model: str
    request_timestamp: datetime
    latency_ms: int
    token_usage: Optional[dict[str, int]] = None
    validation_status: str = "valid"
    error: Optional[str] = None

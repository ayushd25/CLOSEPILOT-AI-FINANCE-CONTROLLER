from datetime import datetime

from app.utils import utcnow
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    UNPROCESSED = "UNPROCESSED"
    MATCHED = "MATCHED"
    AUTO_RESOLVED = "AUTO_RESOLVED"
    EXCEPTION = "EXCEPTION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OutcomeType(str, Enum):
    EXACT_MATCH = "exact_match"
    PROBABLE_MATCH = "probable_match"
    DUPLICATE = "duplicate"
    MISSING_SETTLEMENT = "missing_settlement"
    MISSING_BANK_TRANSACTION = "missing_bank_transaction"
    AMOUNT_MISMATCH = "amount_mismatch"
    FEE_DISCREPANCY = "fee_discrepancy"
    TAX_DISCREPANCY = "tax_discrepancy"
    DATE_DRIFT = "date_drift"
    PARTIAL_SETTLEMENT = "partial_settlement"
    SPLIT_SETTLEMENT = "split_settlement"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    CONFLICTING_CANDIDATES = "conflicting_candidates"
    SUSPICIOUS = "suspicious"
    UNRESOLVABLE = "unresolvable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AIProposal(BaseModel):
    case_id: str
    conclusion: str = "INSUFFICIENT_EVIDENCE"
    root_cause: Optional[str] = None
    confidence: float = 0.0
    risk_level: RiskLevel = RiskLevel.HIGH
    proposed_action: str = "KEEP_EXCEPTION"
    evidence_ids: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class Discrepancy(BaseModel):
    amount_diff: int = 0
    currency: str = "INR"
    detail: Optional[str] = None
    fees: Optional[int] = None
    tax: Optional[int] = None


class DeterministicInfo(BaseModel):
    rules_triggered: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    signal_values: dict[str, Any] = Field(default_factory=dict)
    calculated_difference: int = 0
    tolerance_used: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    match_score: float = 0.0


class ReconciliationCase(BaseModel):
    case_id: str = Field(default_factory=lambda: "")
    related_record_ids: list[str] = Field(default_factory=list)
    candidate_matches: list[dict] = Field(default_factory=list)
    status: CaseStatus = CaseStatus.UNPROCESSED
    match_score: float = 0.0
    outcome_type: Optional[str] = None
    deterministic_info: Optional[DeterministicInfo] = None
    discrepancy: Optional[Discrepancy] = None
    root_cause: Optional[str] = None
    risk: RiskLevel = RiskLevel.LOW
    ai_proposal: Optional[AIProposal] = None
    final_action: Optional[str] = None
    reviewer: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    source: str = "synthetic"
    record_type: str = "payment"
    amount: int = 0
    currency: str = "INR"

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "ReconciliationCase":
        if "_id" in doc and ("case_id" not in doc or doc.get("case_id") == ""):
            doc["case_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        try:
            return cls(**doc)
        except Exception:
            return cls(**{k: v for k, v in doc.items() if k not in (
                "deterministic_info", "ai_proposal", "discrepancy"
            )})


class PolicyDecision(BaseModel):
    allowed: bool = False
    decision: str = "DENY"
    reason_codes: list[str] = Field(default_factory=list)
    required_role: Optional[str] = None
    evidence_requirements: list[str] = Field(default_factory=list)
    policy_version: str = "1.0"

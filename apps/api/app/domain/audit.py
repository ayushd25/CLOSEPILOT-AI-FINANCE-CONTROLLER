from datetime import datetime

from app.utils import utcnow
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    CASE_CREATED = "CASE_CREATED"
    MATCH_PROPOSED = "MATCH_PROPOSED"
    AI_INVESTIGATION_STARTED = "AI_INVESTIGATION_STARTED"
    AI_INVESTIGATION_COMPLETED = "AI_INVESTIGATION_COMPLETED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    AUTO_RESOLVED = "AUTO_RESOLVED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    EXCEPTION_CREATED = "EXCEPTION_CREATED"
    SYNC_STARTED = "SYNC_STARTED"
    SYNC_COMPLETED = "SYNC_COMPLETED"

    def __str__(self) -> str:
        return self.value


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: "")
    case_id: Optional[str] = None
    event_type: str = ""
    actor_type: str = "system"
    actor_id: Optional[str] = None
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    evidence_ids: list[str] = Field(default_factory=list)
    policy_decision: Optional[dict[str, Any]] = None
    model_metadata: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=utcnow)
    correlation_id: Optional[str] = None
    detail: Optional[str] = None

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "AuditEvent":
        if "_id" in doc and ("event_id" not in doc or doc.get("event_id") == ""):
            doc["event_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)

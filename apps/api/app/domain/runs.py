from datetime import datetime

from app.utils import utcnow
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReconciliationRun(BaseModel):
    run_id: str = Field(default_factory=lambda: "")
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: Optional[datetime] = None
    status: str = "pending"
    total_records: int = 0
    matched: int = 0
    exceptions: int = 0
    auto_resolved: int = 0
    human_review: int = 0
    duration_seconds: float = 0.0
    source: str = "hybrid"

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "ReconciliationRun":
        if "_id" in doc and ("run_id" not in doc or doc.get("run_id") == ""):
            doc["run_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)


class GroundTruth(BaseModel):
    case_id: str
    expected_relationships: list[dict[str, str]] = Field(default_factory=list)
    expected_outcome: str = ""
    expected_auto_or_human: str = "human"
    root_cause: Optional[str] = None
    related_record_ids: list[str] = Field(default_factory=list)

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict) -> "GroundTruth":
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)

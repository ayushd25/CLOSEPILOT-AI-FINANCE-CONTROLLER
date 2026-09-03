from datetime import datetime

from app.utils import utcnow
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EvidenceSource(str, Enum):
    SYNTHETIC = "synthetic"
    SYSTEM_CALCULATION = "system_calculation"
    HUMAN = "human"


class EdgeType(str, Enum):
    MATCHED_TO = "MATCHED_TO"
    SETTLED_AS = "SETTLED_AS"
    EXPLAINED_BY = "EXPLAINED_BY"
    GENERATED_FROM = "GENERATED_FROM"
    REFUNDED_BY = "REFUNDED_BY"
    ADJUSTED_BY = "ADJUSTED_BY"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    DERIVED_FROM = "DERIVED_FROM"


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: "")
    entity_type: str = "financial_record"
    entity_id: str = ""
    type: str = "fact"
    source: EvidenceSource = EvidenceSource.SYSTEM_CALCULATION
    source_record_id: Optional[str] = None
    statement: str = ""
    extracted_value: Optional[Any] = None
    timestamp: datetime = Field(default_factory=utcnow)
    created_by: str = "system"
    provenance: dict[str, Any] = Field(default_factory=dict)
    case_id: Optional[str] = None

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "EvidenceItem":
        if "_id" in doc and ("evidence_id" not in doc or doc.get("evidence_id") == ""):
            doc["evidence_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)


class EvidenceEdge(BaseModel):
    source: str
    target: str
    edge_type: EdgeType
    label: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceGraph(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)

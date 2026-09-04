from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.utils import utcnow


class PolicyThresholds(BaseModel):
    """Numeric gates used by the policy engine (thresholds can be edited)."""

    confidence_threshold: float = 0.7
    max_auto_tolerance: int = 200  # minor units
    high_impact_threshold: int = 50_00_000  # minor units (₹50,000.00)
    min_evidence_ids: int = 2
    auto_close_match_score: float = 100.0


class PolicyRuleToggles(BaseModel):
    """On/off switches for individual rule gates in the engine."""

    enforce_high_impact_gate: bool = True
    auto_close_medium_risk: bool = False
    auto_close_high_risk: bool = False
    enforce_multi_candidate_gate: bool = True
    enforce_discrepancy_tolerance: bool = True
    require_low_risk_for_deterministic_auto_close: bool = True


class PolicyConfig(BaseModel):
    config_id: str = Field(default_factory=lambda: "default")
    enabled: bool = True
    version: int = 1
    thresholds: PolicyThresholds = Field(default_factory=PolicyThresholds)
    toggles: PolicyRuleToggles = Field(default_factory=PolicyRuleToggles)
    description: str = "Default policy configuration"
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by: str = "system"
    change_note: str = "Initial policy configuration"

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "PolicyConfig":
        if "_id" in doc and ("config_id" not in doc or doc.get("config_id") == ""):
            doc["config_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)


def default_policy_config() -> PolicyConfig:
    return PolicyConfig()
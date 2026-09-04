from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.domain.cases import AIProposal, PolicyDecision
from app.utils import utcnow


class AgentIntent(str, Enum):
    QUESTION = "QUESTION"
    TASK = "TASK"


class AgentRunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentEventType(str, Enum):
    RUN_STARTED = "RUN_STARTED"
    INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
    PLAN_CREATED = "PLAN_CREATED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_SUCCEEDED = "TOOL_SUCCEEDED"
    TOOL_FAILED = "TOOL_FAILED"
    ACTION_GATED = "ACTION_GATED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_DENIED = "ACTION_DENIED"
    STEP_COMPLETED = "STEP_COMPLETED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"


class AgentToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentPlanStep(BaseModel):
    step: int
    action: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    message: Optional[str] = None
    result_summary: Optional[str] = None


class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: "")
    run_id: str
    event_type: str
    message: str = ""
    tool: Optional[str] = None
    step: Optional[int] = None
    data: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=utcnow)

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "AgentEvent":
        if "_id" in doc and ("event_id" not in doc or doc.get("event_id") == ""):
            doc["event_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)


class AgentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: "")
    session_id: str
    request_text: str
    intent: AgentIntent = AgentIntent.QUESTION
    status: AgentRunStatus = AgentRunStatus.RUNNING
    plan: list[AgentPlanStep] = Field(default_factory=list)
    answer: Optional[str] = None
    executed_actions: int = 0
    staged_actions: int = 0
    denied_actions: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: Optional[datetime] = None

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "AgentRun":
        if "_id" in doc and ("run_id" not in doc or doc.get("run_id") == ""):
            doc["run_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)


class AgentResponse(BaseModel):
    run_id: str
    intent: AgentIntent
    status: AgentRunStatus
    answer: Optional[str] = None
    events: list[AgentEvent] = Field(default_factory=list)
    summary: Optional[dict[str, Any]] = None
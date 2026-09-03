from app.utils import utcnow
from typing import Any, Optional
from uuid import uuid4

from app.db import Database
from app.domain.audit import AuditEvent


class AuditService:
    def __init__(self):
        self.db = Database.get_db()

    async def record(
        self,
        event_type: str,
        case_id: Optional[str] = None,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        evidence_ids: Optional[list[str]] = None,
        policy_decision: Optional[dict] = None,
        model_metadata: Optional[dict] = None,
        detail: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        event = AuditEvent(
            event_id=str(uuid4()),
            case_id=case_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            before_state=before_state,
            after_state=after_state,
            evidence_ids=evidence_ids or [],
            policy_decision=policy_decision,
            model_metadata=model_metadata,
            detail=detail,
            correlation_id=correlation_id or str(uuid4()),
            timestamp=utcnow(),
        )
        result = await self.db.audit_events.insert_one(event.to_mongo())
        return str(result.inserted_id)

    async def list_events(self, case_id: Optional[str] = None, limit: int = 100, skip: int = 0) -> list[AuditEvent]:
        query: dict[str, Any] = {}
        if case_id:
            query["case_id"] = case_id
        cursor = self.db.audit_events.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [AuditEvent.from_mongo(d) for d in docs]

    async def replay(self, case_id: str) -> list[AuditEvent]:
        events_by_case = await self.db.audit_events.find({"case_id": case_id}).sort("timestamp", 1).to_list(length=1000)
        events_by_record = await self.db.audit_events.find(
            {"detail": {"$regex": case_id, "$options": "i"}}
        ).sort("timestamp", 1).to_list(length=1000)

        all_events = events_by_case + events_by_record
        dedup = {}
        for doc in all_events:
            dedup[doc.get("event_id") or str(doc.get("_id"))] = doc
        sorted_events = sorted(dedup.values(), key=lambda d: d.get("timestamp", ""))
        return [AuditEvent.from_mongo(d) for d in sorted_events]

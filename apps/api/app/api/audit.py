from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.db import Database

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit(limit: int = 100, skip: int = 0):
    from app.audit.service import AuditService

    audit = AuditService()
    events = await audit.list_events(limit=limit, skip=skip)
    return {"total": len(events), "events": [e.to_mongo() for e in events]}


@router.get("/cases/{case_id}")
async def get_case_audit(case_id: str):
    from app.audit.service import AuditService

    audit = AuditService()
    events = await audit.list_events(case_id=case_id)
    return {"case_id": case_id, "events": [e.to_mongo() for e in events]}

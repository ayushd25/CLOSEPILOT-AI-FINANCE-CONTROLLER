from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.db import Database
from app.reconciliation.engine import ReconciliationEngine

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.post("/run")
async def run_reconciliation(source: Optional[str] = "hybrid"):
    engine = ReconciliationEngine()
    run = await engine.run(source=source)
    return run.to_mongo()


@router.get("/runs")
async def get_runs(limit: int = 20, skip: int = 0):
    db = Database.get_db()
    cursor = db.reconciliation_runs.find({}).sort("started_at", -1).skip(skip).limit(limit)
    runs = await cursor.to_list(length=limit)
    for r in runs:
        r["run_id"] = str(r.get("_id"))
        r.pop("_id", None)
    return {"runs": runs, "total": len(runs)}


@router.get("/cases")
async def list_cases(
    status: Optional[str] = None,
    risk: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
):
    from app.reconciliation.repositories import ReconciliationCaseRepository

    repo = ReconciliationCaseRepository()
    cases, total = await repo.list_cases(status=status, risk=risk, limit=limit, skip=skip)
    return {
        "total": total,
        "cases": [c.to_mongo() for c in cases],
    }


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    from app.reconciliation.repositories import ReconciliationCaseRepository

    repo = ReconciliationCaseRepository()
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case.to_mongo()


@router.post("/cases/{case_id}/replay")
async def replay_case(case_id: str):
    from app.audit.service import AuditService

    audit = AuditService()
    events = await audit.replay(case_id)
    return {
        "case_id": case_id,
        "events": [e.to_mongo() for e in events],
    }

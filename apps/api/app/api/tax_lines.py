from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.audit.service import AuditService
from app.db import Database
from app.domain.tax_match import TaxMatch, TaxMatchStatus
from app.utils import utcnow

router = APIRouter(prefix="/reconciliation/tax-lines", tags=["tax"])


class ReviewRequest(BaseModel):
    action: str
    note: Optional[str] = None


@router.post("/run")
async def run_tax_match(ai: bool = Query(True, description="Explain exceptions with AI after deterministic classification")):
    from app.reconciliation.tax_matcher import TaxLineMatcher

    matcher = TaxLineMatcher()
    return await matcher.run(run_ai=ai)


@router.get("")
async def list_tax_matches(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
):
    db = Database.get_db()
    query: dict = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"transaction_id": {"$regex": search, "$options": "i"}},
            {"reference": {"$regex": search, "$options": "i"}},
            {"invoice_id": {"$regex": search, "$options": "i"}},
        ]
    cursor = db.tax_matches.find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    total = await db.tax_matches.count_documents(query)
    return {"total": total, "matches": [TaxMatch.from_mongo(d).to_mongo() for d in docs]}


@router.get("/metrics")
async def tax_metrics():
    db = Database.get_db()
    total = await db.tax_matches.count_documents({})
    verified = await db.tax_matches.count_documents({"status": "VERIFIED"})
    exceptions = await db.tax_matches.count_documents({"status": "EXCEPTION"})
    human_review = await db.tax_matches.count_documents({"status": "HUMAN_REVIEW"})
    return {
        "checked": total,
        "verified": verified,
        "exceptions": exceptions,
        "human_review": human_review,
        "match_rate": round(verified / total, 4) if total else 0.0,
    }


@router.get("/{match_id}")
async def get_tax_match(match_id: str):
    db = Database.get_db()
    doc = await db.tax_matches.find_one({"match_id": match_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Tax match {match_id} not found")
    return TaxMatch.from_mongo(doc).to_mongo()


@router.post("/{match_id}/review")
async def review_tax_match(match_id: str, req: ReviewRequest, role: Optional[str] = Header(None, alias="X-User-Role")):
    db = Database.get_db()
    doc = await db.tax_matches.find_one({"match_id": match_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Tax match {match_id} not found")

    action = req.action.upper()
    valid = {s.value for s in TaxMatchStatus}
    if action not in valid:
        raise HTTPException(status_code=400, detail=f"action must be one of {sorted(valid)}")

    before = {"status": doc.get("status")}
    await db.tax_matches.update_one(
        {"match_id": match_id},
        {"$set": {
            "status": action,
            "reviewed_by": role,
            "review_note": req.note,
            "updated_at": utcnow(),
        }},
    )
    await AuditService().record(
        event_type="TAX_MATCH_REVIEWED",
        case_id=doc.get("case_id"),
        actor_type="human",
        actor_id=role,
        before_state=before,
        after_state={"status": action},
        detail=f"Tax line {doc.get('transaction_id')} reviewed -> {action}: {req.note or ''}",
    )
    updated = await db.tax_matches.find_one({"match_id": match_id})
    return TaxMatch.from_mongo(updated).to_mongo()
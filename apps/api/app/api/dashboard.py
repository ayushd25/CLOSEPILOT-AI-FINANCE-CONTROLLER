from fastapi import APIRouter, Query
from typing import Optional

from app.db import Database

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary():
    db = Database.get_db()

    total_records = await db.financial_records.count_documents({})
    total_cases = await db.reconciliation_cases.count_documents({})
    reconciled = await db.reconciliation_cases.count_documents({"status": {"$in": ["AUTO_RESOLVED", "RESOLVED", "MATCHED"]}})
    auto_resolved = await db.reconciliation_cases.count_documents({"status": "AUTO_RESOLVED"})
    human_review = await db.reconciliation_cases.count_documents({"status": "HUMAN_REVIEW"})
    exceptions = await db.reconciliation_cases.count_documents({"status": "EXCEPTION"})
    unmatched = await db.reconciliation_cases.count_documents({"status": "UNPROCESSED"})

    total_payments = await db.financial_records.count_documents({"record_type": "payment"})
    total_settlements = await db.financial_records.count_documents({"record_type": "settlement"})
    total_bank = await db.financial_records.count_documents({"record_type": "bank_transaction"})

    precision = 0.0
    recall = 0.0
    false_auto_match = 0.0

    latest_eval = await db.evaluation_runs.find_one({}, sort=[("created_at", -1)])
    if latest_eval:
        methods = latest_eval.get("methods", {})
        cp = methods.get("closepilot", {})
        precision = cp.get("precision", 0)
        recall = cp.get("recall", 0)
        false_auto_match = cp.get("false_auto_match_rate", 0)

    return {
        "total_records": total_records,
        "total_cases": total_cases,
        "reconciled": reconciled,
        "auto_resolved": auto_resolved,
        "human_review": human_review,
        "exceptions": exceptions,
        "unmatched": unmatched,
        "total_payments": total_payments,
        "total_settlements": total_settlements,
        "total_bank_transactions": total_bank,
        "precision": precision,
        "recall": recall,
        "false_auto_match_rate": false_auto_match,
    }


@router.get("/trends")
async def dashboard_trends():
    db = Database.get_db()

    recent_runs = await db.reconciliation_runs.find({}).sort("started_at", -1).limit(30).to_list(length=30)

    from collections import Counter
    risk_dist = Counter()
    async for case in db.reconciliation_cases.find({}):
        risk_dist[case.get("risk", "LOW")] += 1

    source_health = {
        "synthetic": {
            "records": await db.financial_records.count_documents({"source": "synthetic"}),
        },
    }

    return {
        "reconciliation_runs": [
            {
                "run_id": r.get("run_id"),
                "started_at": r.get("started_at"),
                "total_records": r.get("total_records"),
                "matched": r.get("matched"),
                "exceptions": r.get("exceptions"),
                "auto_resolved": r.get("auto_resolved"),
                "duration_seconds": r.get("duration_seconds"),
            }
            for r in recent_runs
        ],
        "risk_distribution": dict(risk_dist),
        "source_health": source_health,
    }

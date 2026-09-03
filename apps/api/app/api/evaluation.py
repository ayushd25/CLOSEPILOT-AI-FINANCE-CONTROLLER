from fastapi import APIRouter, HTTPException
from typing import Optional

from app.db import Database

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/run")
async def run_evaluation(dataset_id: str, methods: Optional[list[str]] = None):
    from app.evaluation.service import EvaluationService

    service = EvaluationService()
    result = await service.run_benchmark(dataset_id, methods)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/runs")
async def list_evaluation_runs(limit: int = 20):
    db = Database.get_db()
    cursor = db.evaluation_runs.find({}).sort("created_at", -1).limit(limit)
    runs = await cursor.to_list(length=limit)
    for r in runs:
        r["run_id"] = str(r.get("_id"))
        r.pop("_id", None)
    return {"runs": runs}


@router.get("/runs/{run_id}")
async def get_evaluation_run(run_id: str):
    db = Database.get_db()
    from bson.objectid import ObjectId

    try:
        doc = await db.evaluation_runs.find_one({"_id": ObjectId(run_id)})
    except Exception:
        doc = await db.evaluation_runs.find_one({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Evaluation run {run_id} not found")
    doc["run_id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc


@router.get("/baselines")
async def get_baselines():
    from app.synthetic.generator import SCENARIO_CATALOG

    return {
        "baselines": [
            {"name": "exact_id", "description": "Exact ID/reference matching"},
            {"name": "amount_date", "description": "Amount + date threshold matching"},
            {"name": "fuzzy", "description": "Fuzzy reference + amount similarity"},
            {"name": "closepilot", "description": "Full ClosePilot deterministic engine"},
        ],
        "scenario_catalog": SCENARIO_CATALOG,
    }

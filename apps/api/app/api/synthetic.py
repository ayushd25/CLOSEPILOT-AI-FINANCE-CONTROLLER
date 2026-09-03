from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.db import Database

router = APIRouter(prefix="/synthetic", tags=["synthetic"])


class GenerateRequest(BaseModel):
    n_cases: int = 100
    scenario_mix: Optional[dict[str, int]] = None
    seed: int = 42


@router.post("/generate")
async def generate_synthetic(req: GenerateRequest):
    from app.synthetic.generator import SyntheticDataSource
    from app.domain.runs import GroundTruth

    gen = SyntheticDataSource()
    records, ground_truths, info = await gen.generate(
        n_cases=req.n_cases,
        scenario_mix=req.scenario_mix,
        seed=req.seed,
    )

    db = Database.get_db()

    # Store records
    inserted = 0
    for rec in records:
        doc = rec.to_mongo()
        existing = await db.financial_records.find_one({
            "record_type": rec.record_type,
            "external_id": rec.external_id,
            "source": "synthetic",
        })
        if existing:
            continue
        await db.financial_records.insert_one(doc)
        inserted += 1

    # Store ground truth (separate collection - never exposed to AI)
    gt_inserted = 0
    for gt in ground_truths:
        gt_doc = GroundTruth(
            case_id=gt["case_id"],
            expected_relationships=gt.get("expected_relationships", []),
            expected_outcome=gt.get("expected_outcome", ""),
            expected_auto_or_human=gt.get("expected_auto_or_human", "human"),
            root_cause=gt.get("root_cause"),
            related_record_ids=gt.get("related_record_ids", []),
        )
        existing_gt = await db.ground_truth.find_one({"case_id": gt["case_id"]})
        if existing_gt:
            continue
        await db.ground_truth.insert_one(gt_doc.to_mongo())
        gt_inserted += 1

    info["inserted_records"] = inserted
    info["inserted_ground_truths"] = gt_inserted
    return info


@router.get("/datasets")
async def list_datasets():
    db = Database.get_db()
    cursor = db.synthetic_datasets.find({}).sort("created_at", -1).limit(50)
    datasets = await cursor.to_list(length=50)
    for d in datasets:
        d["dataset_id"] = str(d.get("_id"))
        d.pop("_id", None)
    return {"datasets": datasets}

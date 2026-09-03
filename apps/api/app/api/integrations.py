from fastapi import APIRouter, HTTPException

from app.integrations.razorpay.service import RazorpayService

router = APIRouter(prefix="/integrations/razorpay", tags=["razorpay"])


@router.get("/status")
async def razorpay_status():
    service = RazorpayService()
    status = await service.get_status()
    return status


@router.post("/sync")
async def razorpay_sync():
    service = RazorpayService()
    run = await service.sync()
    return run.to_mongo()


@router.get("/sync-runs")
async def list_sync_runs(limit: int = 20):
    from app.db import Database

    db = Database.get_db()
    cursor = db.sync_runs.find({}).sort("started_at", -1).limit(limit)
    runs = await cursor.to_list(length=limit)
    for r in runs:
        r["sync_run_id"] = str(r.get("_id"))
        r.pop("_id", None)
    return {"runs": runs}


@router.get("/configuration")
async def razorpay_configuration():
    from app.config import settings

    return {
        "mode": settings.RAZORPAY_MODE,
        "key_id_configured": bool(settings.RAZORPAY_KEY_ID),
        "secret_configured": bool(settings.RAZORPAY_KEY_SECRET),
        "page_size": settings.RAZORPAY_PAGE_SIZE,
        "timeout_seconds": settings.RAZORPAY_TIMEOUT_SECONDS,
    }

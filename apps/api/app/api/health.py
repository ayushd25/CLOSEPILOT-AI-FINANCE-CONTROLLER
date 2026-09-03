from fastapi import APIRouter, Depends

from app.db import Database

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "closepilot-api"}


@router.get("/ready")
async def ready():
    try:
        db = Database.get_db()
        await db.command("ping")
        return {"status": "ready", "mongo": "connected"}
    except Exception:
        return {"status": "degraded", "mongo": "unavailable"}

from fastapi import APIRouter, Depends

from app.db import Database

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "closepilot-api"}


@router.get("/ready")
async def ready():
    Database.get_db()
    return {"status": "ready", "store": "in-memory"}

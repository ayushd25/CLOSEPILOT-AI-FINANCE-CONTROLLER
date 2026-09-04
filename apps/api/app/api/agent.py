from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.agent.supervisor import AgentSupervisor
from app.db import Database

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
async def agent_chat(payload: dict):
    request_text = (payload.get("request") or payload.get("message") or "").strip()
    if not request_text:
        raise HTTPException(status_code=400, detail="message is required")
    session_id = payload.get("session_id")
    role = payload.get("role") or "FINANCE_CONTROLLER"
    agent = AgentSupervisor(session_id=session_id, role=role)
    response = await agent.run(request_text)
    return response.model_dump()


@router.get("/runs/{run_id}")
async def get_agent_run(run_id: str):
    db = Database.get_db()
    doc = await db.agent_runs.find_one({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    from app.domain.agent import AgentRun

    run = AgentRun.from_mongo(doc)
    agent = AgentSupervisor(session_id=run.session_id)
    events = await agent.get_events(run_id)
    return {
        **run.model_dump(),
        "events": [e.model_dump() for e in events],
    }


@router.get("/runs/{run_id}/events")
async def get_agent_events(run_id: str, limit: int = Query(100, ge=1, le=500)):
    agent = AgentSupervisor()
    try:
        events = await agent.get_events(run_id, limit=limit)
    except LookupError:
        # events collection may be empty; still return ok
        events = []
    return {"events": [e.model_dump() for e in events]}
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi import Body

from app.db import Database
from app.domain.policy_config import PolicyConfig, default_policy_config
from app.policy.repository import PolicyConfigRepository

router = APIRouter(prefix="/policy", tags=["policy"])


# -------------------------------- schemas -------------------------------- #


def _reverse_diff(before: dict, after: dict) -> list[dict]:
    """Return a compact list of rule fields whose value changed (used for audit).

    Only meaningful rule settings are compared (thresholds + toggles). Meta
    fields like version/updated_at are excluded to keep the audit focused.
    """
    diffs = []
    for group in ("thresholds", "toggles"):
        b = before.get(group) or {}
        a = after.get(group) or {}
        for k in set(b.keys()) | set(a.keys()):
            if b.get(k) != a.get(k):
                diffs.append({"field": f"{group}.{k}", "from": b.get(k), "to": a.get(k)})
    return diffs


# -------------------------------- routes -------------------------------- #


@router.get("")
async def get_policy():
    repo = PolicyConfigRepository()
    cfg = await repo.get()
    return cfg.to_mongo()


@router.get("/defaults")
async def get_defaults():
    cfg = default_policy_config()
    return cfg.to_mongo()


@router.put("")
async def update_policy(
    payload: dict[str, Any] = Body(...),
):
    th = payload.get("thresholds") or {}
    tg = payload.get("toggles") or {}
    updated_by = payload.get("updated_by") or "admin"
    change_note = payload.get("change_note") or "Policy updated via admin UI"

    repo = PolicyConfigRepository()
    before_cfg = await repo.get()

    try:
        new_cfg = await repo.update(
            thresholds=th,
            toggles=tg,
            updated_by=updated_by,
            change_note=change_note,
        )
    except Exception as e:  # pragma: no cover - validation errors surface upstream
        raise HTTPException(status_code=400, detail=f"Invalid policy update: {e}")

    diffs = _reverse_diff(before_cfg.to_mongo(), new_cfg.to_mongo())

    from app.audit.service import AuditService

    audit = AuditService()
    await audit.record(
        event_type="POLICY_UPDATED",
        actor_type="user",
        actor_id=updated_by,
        before_state=before_cfg.to_mongo(),
        after_state=new_cfg.to_mongo(),
        policy_decision={"decision": "ALLOW", "reason_codes": ["policy_config_change"]},
        model_metadata={"policy_version": new_cfg.version, "changes": diffs},
        detail=f"Policy config updated to version {new_cfg.version}",
    )

    return {"config": new_cfg.to_mongo(), "changes": diffs, "version": new_cfg.version}


@router.get("/audit")
async def policy_audit(limit: int = 100):
    db = Database.get_db()
    cursor = db.audit_events.find({"event_type": "POLICY_UPDATED"}).sort("timestamp", -1).limit(limit)
    events = await cursor.to_list(length=limit)
    events = [dict(e) for e in events]
    for e in events:
        e.pop("_id", None)
    return {"total": len(events), "updates": events}
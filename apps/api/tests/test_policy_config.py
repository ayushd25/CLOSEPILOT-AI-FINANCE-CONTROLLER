import pytest

from app.domain.policy_config import default_policy_config
from app.db import Database
from app.policy.repository import PolicyConfigRepository
from app.policy.engine import PolicyEngine

pytestmark = pytest.mark.asyncio

MONGODB_AVAILABLE = None


async def _mongodb_available() -> bool:
    try:
        from app.db import Database

        db = Database.get_db()
        await db.command("ping")
        return True
    except Exception:
        return False


async def _require_mongodb():
    global MONGODB_AVAILABLE
    if MONGODB_AVAILABLE is None:
        MONGODB_AVAILABLE = await _mongodb_available()
    if not MONGODB_AVAILABLE:
        pytest.skip("MongoDB not available; skipping policy config integration test")


async def test_default_config_matches_engine_builtins():
    cfg = default_policy_config()
    assert cfg.thresholds.confidence_threshold == 0.7
    assert cfg.thresholds.max_auto_tolerance == 200
    assert cfg.thresholds.high_impact_threshold == 50_00_000
    assert cfg.thresholds.min_evidence_ids == 2
    assert cfg.toggles.auto_close_medium_risk is False
    assert cfg.toggles.auto_close_high_risk is False
    assert cfg.toggles.enforce_multi_candidate_gate is True


async def test_engine_toggle_gates_medium_risk():
    from app.domain.policy_config import PolicyConfig, PolicyRuleToggles
    from app.domain.cases import (
        AIProposal, DeterministicInfo, Discrepancy, ReconciliationCase, RiskLevel, CaseStatus,
    )

    case = ReconciliationCase(
        case_id="CASE_MED",
        status=CaseStatus.AUTO_RESOLVED,
        match_score=60,
        risk=RiskLevel.MEDIUM,
        amount=1000,
        discrepancy=Discrepancy(amount_diff=0, currency="INR"),
        deterministic_info=DeterministicInfo(match_score=60, candidate_ids=[], reason_codes=["t"]),
    )
    proposal = AIProposal(
        case_id="CASE_MED",
        conclusion="EXPLAINED_DISCREPANCY",
        confidence=0.9,
        risk_level=RiskLevel.MEDIUM,
        proposed_action="AUTO_CLOSE",
        evidence_ids=["e1", "e2"],
        reason_codes=["fee_explains"],
    )

    # Default: MEDIUM proposal risk blocked
    engine_default = PolicyEngine()
    d1 = await engine_default.evaluate(case, proposal)
    assert d1.decision == "HUMAN_REVIEW"

    # Toggle enabled: MEDIUM proposal risk allowed -> AUTO_CLOSE
    cfg = PolicyConfig(
        config_id="t1",
        toggles=PolicyRuleToggles(auto_close_medium_risk=True),
    )
    engine_toggled = PolicyEngine()._set_config(cfg)
    d2 = await engine_toggled.evaluate(case, proposal)
    assert d2.decision == "AUTO_CLOSE"


async def test_repository_seeds_and_persists_update():
    await _require_mongodb()
    db = Database.get_db()
    await db.policy_config.delete_many({})
    await db.audit_events.delete_many({"event_type": "POLICY_UPDATED"})

    repo = PolicyConfigRepository()
    repo._cache = None

    first = await repo.get()
    assert first.version == 1
    assert first.thresholds.confidence_threshold == 0.7

    updated = await repo.update(
        thresholds={"confidence_threshold": 0.8, "max_auto_tolerance": 500},
        toggles={"auto_close_medium_risk": True},
        updated_by="tester",
        change_note="test update",
    )
    assert updated.version == first.version + 1
    assert updated.thresholds.confidence_threshold == 0.8
    assert updated.thresholds.max_auto_tolerance == 500
    assert updated.toggles.auto_close_medium_risk is True

    # Reload from a fresh repo (no cache) to prove persistence
    repo2 = PolicyConfigRepository()
    repo2._cache = None
    reloaded = await repo2.get()
    assert reloaded.version == updated.version
    assert reloaded.thresholds.confidence_threshold == 0.8
    assert reloaded.toggles.auto_close_medium_risk is True

    await db.policy_config.delete_many({})
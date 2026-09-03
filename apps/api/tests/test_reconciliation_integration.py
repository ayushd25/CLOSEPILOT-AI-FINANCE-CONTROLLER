"""Integration tests that require a running MongoDB instance.

These tests exercise the full reconciliation pipeline against a real
database. They are skipped automatically when MongoDB is not reachable so
the pure unit-test suite remains standalone and fast.
"""

import asyncio
import pytest

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
        pytest.skip("MongoDB not available; skipping integration test")


async def _fresh_db():
    from app.db import Database
    db = Database.get_db()
    for collection in (
        "financial_records",
        "reconciliation_cases",
        "reconciliation_runs",
        "audit_events",
        "evidence_items",
        "ground_truth",
        "synthetic_datasets",
    ):
        await db[collection].delete_many({})
    return db


async def test_reconciliation_produces_mapped_statuses():
    await _require_mongodb()
    db = await _fresh_db()

    from app.db.indexes import ensure_indexes
    await ensure_indexes()

    from app.synthetic.generator import SyntheticDataSource
    gen = SyntheticDataSource()
    records, ground_truths, _ = await gen.generate(n_cases=20, seed=42)

    for rec in records:
        await db.financial_records.insert_one(rec.to_mongo())

    from app.reconciliation.engine import ReconciliationEngine
    engine = ReconciliationEngine()
    run = await engine.run(source="synthetic")

    assert run.status == "completed"
    assert run.total_records == len(records)
    assert run.matched + run.exceptions + run.auto_resolved + run.human_review == len(records)

    cases = await db.reconciliation_cases.find({}).to_list(length=100000)
    statuses = {c["status"] for c in cases}
    assert statuses and statuses.issubset(
        {"MATCHED", "EXCEPTION", "HUMAN_REVIEW", "AUTO_RESOLVED"}
    ), f"Unexpected statuses: {statuses}"
    assert "UNPROCESSED" not in statuses, "Some cases were left UNPROCESSED"

    for c in cases:
        assert c["case_id"], "Case missing case_id"
        assert c["case_id"].startswith("CASE_"), f"Unexpected case_id {c['case_id']}"


async def test_case_id_consistent_between_find_and_insert():
    await _require_mongodb()
    db = await _fresh_db()

    from app.synthetic.generator import SyntheticDataSource
    gen = SyntheticDataSource()
    records, _, _ = await gen.generate(n_cases=3, seed=7)
    for rec in records:
        await db.financial_records.insert_one(rec.to_mongo())

    from app.reconciliation.engine import ReconciliationEngine
    engine = ReconciliationEngine()
    await engine.run(source="synthetic")

    cases = await db.reconciliation_cases.find({}).to_list(length=1000)
    assert cases, "Expected at least one case to be created"
    for c in cases:
        dup = await db.reconciliation_cases.find_one({"case_id": c["case_id"]})
        assert dup is not None, f"Case {c['case_id']} not retrievable by case_id"
        assert str(dup["_id"]) != c["case_id"], "case_id should not be a Mongo ObjectId"


async def test_auto_resolved_low_risk_cases_have_score():
    await _require_mongodb()
    db = await _fresh_db()

    from app.synthetic.generator import SyntheticDataSource
    gen = SyntheticDataSource()
    records, _, _ = await gen.generate(n_cases=20, seed=99)
    for rec in records:
        await db.financial_records.insert_one(rec.to_mongo())

    from app.reconciliation.engine import ReconciliationEngine
    engine = ReconciliationEngine()
    await engine.run(source="synthetic")

    auto = [
        c for c in await db.reconciliation_cases.find({}).to_list(length=100000)
        if c["status"] == "AUTO_RESOLVED"
    ]
    if auto:
        for c in auto:
            assert c["risk"] == "LOW", f"Auto-resolved {c['case_id']} not LOW risk"
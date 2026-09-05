from app.db import Database


async def ensure_indexes() -> None:
    db = Database.get_db()

    await db.financial_records.create_index([("record_type", 1), ("external_id", 1)])
    await db.financial_records.create_index([("source", 1)])
    await db.financial_records.create_index([("amount", 1)])
    await db.financial_records.create_index([("reference", 1)])
    await db.financial_records.create_index([("currency", 1)])
    await db.financial_records.create_index([("transaction_at", 1)])
    await db.financial_records.create_index([("settlement_id", 1)])
    await db.financial_records.create_index([("order_id", 1)])

    await db.reconciliation_cases.create_index([("status", 1)])
    await db.reconciliation_cases.create_index([("risk", 1)])
    await db.reconciliation_cases.create_index([("created_at", -1)])

    await db.evidence_items.create_index([("entity_type", 1), ("entity_id", 1)])
    await db.evidence_items.create_index([("case_id", 1)])

    await db.audit_events.create_index([("case_id", 1)])
    await db.audit_events.create_index([("timestamp", -1)])
    await db.audit_events.create_index([("event_type", 1)])

    await db.evaluation_runs.create_index([("created_at", -1)])
    await db.synthetic_datasets.create_index([("name", 1)])

    await db.agent_runs.create_index([("run_id", 1)])
    await db.agent_runs.create_index([("session_id", 1)])
    await db.agent_runs.create_index([("created_at", -1)])
    await db.agent_events.create_index([("run_id", 1)])
    await db.agent_events.create_index([("created_at", 1)])

    await db.tax_matches.create_index([("match_id", 1)], unique=True)
    await db.tax_matches.create_index([("status", 1)])
    await db.tax_matches.create_index([("transaction_id", 1)])
    await db.tax_matches.create_index([("created_at", -1)])

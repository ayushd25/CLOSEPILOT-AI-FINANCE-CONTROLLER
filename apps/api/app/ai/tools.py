from typing import Any, Optional

from app.db import Database
from app.domain.cases import ReconciliationCase
from app.domain.models import FinancialRecord


class ReadOnlyToolError(Exception):
    pass


class AIReadOnlyTools:
    def __init__(self):
        self.db = Database.get_db()

    @staticmethod
    def _validate_id(entity_type: str, entity_id: str) -> None:
        if not entity_id or not isinstance(entity_id, str):
            raise ReadOnlyToolError(f"Invalid {entity_type} ID: {entity_id}")
        if len(entity_id) > 200:
            raise ReadOnlyToolError(f"Entity ID too long: {len(entity_id)} chars")

    async def get_case(self, case_id: str) -> Optional[dict]:
        self._validate_id("case", case_id)
        doc = await self.db.reconciliation_cases.find_one({"case_id": case_id})
        if not doc:
            return None
        return {
            "case_id": doc.get("case_id"),
            "status": doc.get("status"),
            "outcome_type": doc.get("outcome_type"),
            "risk": doc.get("risk"),
            "amount": doc.get("amount"),
            "currency": doc.get("currency"),
            "related_records": doc.get("related_record_ids", []),
            "candidates": doc.get("candidate_matches", [])[:5],
            "discrepancy": doc.get("discrepancy"),
            "deterministic": doc.get("deterministic_info"),
        }

    async def get_financial_record(self, record_id: str) -> Optional[FinancialRecord]:
        self._validate_id("financial_record", record_id)
        for record_type in (
            "payment", "order", "settlement", "bank_transaction",
            "invoice", "fee", "tax", "refund", "chargeback", "adjustment",
            "recon_event",
        ):
            doc = await self.db.financial_records.find_one({"record_type": record_type, "external_id": record_id})
            if doc:
                return FinancialRecord.from_mongo(doc)
        # fallback: try by id field
        doc = await self.db.financial_records.find_one({"id": record_id})
        if doc:
            return FinancialRecord.from_mongo(doc)
        return None

    async def get_payment(self, payment_id: str) -> Optional[dict]:
        rec = await self.get_financial_record(payment_id)
        if not rec and not payment_id.startswith("pay"):
            rec = await self.get_financial_record(payment_id)
        if not rec:
            return None
        return {
            "id": rec.external_id,
            "record_type": rec.record_type,
            "amount": rec.amount,
            "currency": rec.currency,
            "status": rec.status,
            "description": rec.description,
            "metadata": rec.metadata,
            "reference": rec.reference,
            "transaction_at": rec.transaction_at,
        }

    async def get_related_records(self, case_id: str) -> list[dict]:
        self._validate_id("case", case_id)
        case_doc = await self.db.reconciliation_cases.find_one({"case_id": case_id})
        if not case_doc:
            return []
        related = []
        for rid in case_doc.get("related_record_ids", []):
            rec = await self.get_financial_record(rid)
            if rec:
                related.append({
                    "id": rec.external_id,
                    "record_type": rec.record_type,
                    "amount": rec.amount,
                    "currency": rec.currency,
                    "status": rec.status,
                    "description": rec.description,
                })
        return related

    async def get_evidence(self, case_id: str) -> list[dict]:
        self._validate_id("case", case_id)
        cursor = self.db.evidence_items.find({"case_id": case_id})
        docs = await cursor.to_list(length=100)
        return [
            {
                "evidence_id": d.get("evidence_id") or str(d.get("_id")),
                "entity_type": d.get("entity_type"),
                "entity_id": d.get("entity_id"),
                "statement": d.get("statement"),
                "source": d.get("source"),
            }
            for d in docs
        ]

    async def get_reconciliation_candidates(self, case_id: str) -> list[dict]:
        self._validate_id("case", case_id)
        case_doc = await self.db.reconciliation_cases.find_one({"case_id": case_id})
        if not case_doc:
            return []
        return case_doc.get("candidate_matches", [])[:10]

    async def get_policy(self) -> dict:
        return {
            "auto_close_requires": [
                "low_risk",
                "no_conflicting_candidates",
                "evidence_complete",
                "discrepancy_within_tolerance",
                "confidence_above_threshold",
            ],
            "human_review_requires": [
                "high_monetary_impact",
                "conflicting_evidence",
                "suspicious_activity",
                "low_confidence",
                "missing_evidence",
                "ai_failure",
            ],
        }

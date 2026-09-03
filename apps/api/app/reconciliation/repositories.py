import hashlib
from typing import Any, Optional, cast

from app.db import Database
from app.domain.cases import ReconciliationCase
from app.domain.models import FinancialRecord


class FinancialRecordRepository:
    def __init__(self, db=None):
        self.db = db if db is not None else Database.get_db()
        self.collection = self.db.financial_records

    async def find_by_external(self, record_type: str, external_id: str) -> Optional[FinancialRecord]:
        doc = await self.collection.find_one({"record_type": record_type, "external_id": external_id})
        return FinancialRecord.from_mongo(doc) if doc else None

    async def find_by_field(self, record_type: str, field: str, value: Any) -> list[FinancialRecord]:
        cursor = self.collection.find({"record_type": record_type, field: value})
        docs = await cursor.to_list(length=10000)
        return [FinancialRecord.from_mongo(d) for d in docs]

    async def find_by_reference(self, reference: str, record_type: Optional[str] = None) -> list[FinancialRecord]:
        query: dict[str, Any] = {"reference": reference}
        if record_type:
            query["record_type"] = record_type
        cursor = self.collection.find(query)
        docs = await cursor.to_list(length=10000)
        return [FinancialRecord.from_mongo(d) for d in docs]

    async def find_by_amount(self, amount: int, record_type: Optional[str] = None, tolerance: int = 0) -> list[FinancialRecord]:
        query: dict[str, Any] = {
            "amount": {"$gte": amount - tolerance, "$lte": amount + tolerance}
        }
        if record_type:
            query["record_type"] = record_type
        cursor = self.collection.find(query)
        docs = await cursor.to_list(length=10000)
        return [FinancialRecord.from_mongo(d) for d in docs]

    async def list_records(
        self,
        record_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 1000,
        skip: int = 0,
    ) -> tuple[list[FinancialRecord], int]:
        query: dict[str, Any] = {}
        if record_type:
            query["record_type"] = record_type
        if source:
            query["source"] = source
        cursor = self.collection.find(query).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        total = await self.collection.count_documents(query)
        return [FinancialRecord.from_mongo(d) for d in docs], total

    async def count(self, query: Optional[dict] = None) -> int:
        return await self.collection.count_documents(query or {})

    async def upsert(self, record: FinancialRecord) -> None:
        existing = await self.collection.find_one({
            "record_type": record.record_type,
            "external_id": record.external_id,
        })
        doc = record.to_mongo()
        if existing:
            await self.collection.update_one({"_id": existing["_id"]}, {"$set": doc})
        else:
            await self.collection.insert_one(doc)


class ReconciliationCaseRepository:
    def __init__(self, db=None):
        self.db = db if db is not None else Database.get_db()
        self.collection = self.db.reconciliation_cases

    async def insert(self, case: ReconciliationCase) -> str:
        doc = case.to_mongo()
        if case.case_id:
            doc["case_id"] = case.case_id
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def update(self, case: ReconciliationCase) -> None:
        doc = case.to_mongo()
        doc.pop("case_id", None)
        doc["updated_at"] = case.updated_at
        await self.collection.update_one({"case_id": case.case_id}, {"$set": doc})

    async def get(self, case_id: str) -> Optional[ReconciliationCase]:
        doc = await self.collection.find_one({"case_id": case_id})
        return ReconciliationCase.from_mongo(doc) if doc else None

    async def list_cases(
        self,
        status: Optional[str] = None,
        risk: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> tuple[list[ReconciliationCase], int]:
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        if risk:
            query["risk"] = risk
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        total = await self.collection.count_documents(query)
        return [ReconciliationCase.from_mongo(d) for d in docs], total

    async def count(self, query: Optional[dict] = None) -> int:
        return await self.collection.count_documents(query or {})

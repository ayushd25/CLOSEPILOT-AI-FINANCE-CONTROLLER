from app.utils import utcnow
from typing import Optional

from app.db import Database
from app.domain.models import FinancialRecord, RecordType, SourceType
from app.domain.runs import SyncRun, SyncRunStatus
from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.mapper import map_order, map_payment, map_recon_event, map_settlement
from app.integrations.razorpay.models import (
    RazorpayOrder,
    RazorpayPayment,
    RazorpaySettlement,
    RazorpaySettlementReconEvent,
)


class RazorpayService:
    def __init__(self, client: Optional[RazorpayClient] = None):
        self.client = client or RazorpayClient()
        self.db = Database.get_db()

    @property
    def is_configured(self) -> bool:
        return self.client.is_configured

    async def get_status(self) -> dict:
        return {
            "connected": self.is_configured,
            "mode": "test",
            "payments": await self.db.financial_records.count_documents({"record_type": "payment"}),
            "settlements": await self.db.financial_records.count_documents({"record_type": "settlement"}),
            "recon_events": await self.db.financial_records.count_documents({"record_type": "recon_event"}),
        }

    async def _upsert(self, record: FinancialRecord) -> tuple[bool, bool]:
        existing = await self.db.financial_records.find_one({
            "record_type": record.record_type,
            "external_id": record.external_id,
        })
        doc = record.to_mongo()
        if existing:
            doc["updated_at"] = utcnow()
            await self.db.financial_records.update_one(
                {"_id": existing["_id"]},
                {"$set": {k: v for k, v in doc.items() if k != "id"}},
            )
            return False, True
        doc["id"] = str(doc.get("id") or "")
        result = await self.db.financial_records.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return True, False

    async def sync(self) -> SyncRun:
        run = SyncRun(source="razorpay_test", status=SyncRunStatus.RUNNING, started_at=utcnow())
        result = await self.db.sync_runs.insert_one(run.to_mongo())
        run.sync_run_id = str(result.inserted_id)
        start = utcnow()

        if not self.is_configured:
            run.status = SyncRunStatus.FAILED
            run.error_summaries.append("Razorpay credentials not configured")
            run.completed_at = utcnow()
            run.duration_seconds = (run.completed_at - start).total_seconds()
            await self.db.sync_runs.update_one({"_id": result.inserted_id}, {"$set": run.to_mongo()})
            return run

        try:
            # Payments with pagination
            skip = 0
            page_size = 100
            while True:
                items = await self.client.get_payments(count=page_size, skip=skip)
                if not items:
                    break
                run.fetched += len(items)
                for item in items:
                    try:
                        p = RazorpayPayment(**item, raw=item)
                        record = map_payment(p, run.sync_run_id)
                        inserted, _ = await self._upsert(record)
                        if inserted:
                            run.inserted += 1
                        else:
                            run.updated += 1
                    except Exception as e:
                        run.errors += 1
                        run.error_summaries.append(f"payment {item.get('id', '?')}: {str(e)[:200]}")
                if len(items) < page_size:
                    break
                skip += page_size

            # Settlements
            skip = 0
            while True:
                items = await self.client.get_settlements(skip=skip, count=page_size)
                if not items:
                    break
                run.fetched += len(items)
                for item in items:
                    try:
                        s = RazorpaySettlement(**item, raw=item)
                        record = map_settlement(s, run.sync_run_id)
                        inserted, _ = await self._upsert(record)
                        if inserted:
                            run.inserted += 1
                        else:
                            run.updated += 1
                    except Exception as e:
                        run.errors += 1
                        run.error_summaries.append(f"settlement {item.get('id', '?')}: {str(e)[:200]}")
                if len(items) < page_size:
                    break
                skip += page_size

            run.status = SyncRunStatus.COMPLETED
        except Exception as e:
            run.status = SyncRunStatus.FAILED
            run.error_summaries.append(f"sync error: {str(e)[:300]}")
            run.errors += 1

        run.completed_at = utcnow()
        run.duration_seconds = (run.completed_at - start).total_seconds()
        await self.db.sync_runs.update_one({"_id": result.inserted_id}, {"$set": run.to_mongo()})
        return run

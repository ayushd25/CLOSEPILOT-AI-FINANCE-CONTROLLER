from datetime import datetime, timezone

from app.utils import utcnow
from typing import Any, Optional

from app.domain.models import FinancialRecord, RecordType, SourceType
from app.integrations.razorpay.models import (
    RazorpayOrder,
    RazorpayPayment,
    RazorpaySettlement,
    RazorpaySettlementReconEvent,
)


def _to_datetime(ts: Optional[int]) -> Optional[datetime]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def map_payment(p: RazorpayPayment, sync_run_id: str) -> FinancialRecord:
    metadata: dict[str, Any] = {}
    if p.order_id:
        metadata["order_id"] = p.order_id
    if p.method:
        metadata["method"] = p.method
    if p.captured:
        metadata["captured"] = p.captured
    if p.fee is not None:
        metadata["fee"] = p.fee
    if p.tax is not None:
        metadata["tax"] = p.tax
    if p.notes:
        metadata["notes"] = p.notes

    return FinancialRecord(
        source=SourceType.RAZORPAY_TEST,
        record_type=RecordType.PAYMENT,
        external_id=p.id,
        amount=p.amount,
        currency=p.currency,
        status="captured" if p.captured else p.status,
        transaction_at=_to_datetime(p.created_at),
        reference=p.order_id,
        description=p.description,
        metadata=metadata,
        raw_payload=p.raw,
        ingested_at=utcnow(),
        sync_run_id=sync_run_id,
        source_record_id=p.id,
    )


def map_order(o: RazorpayOrder, sync_run_id: str) -> FinancialRecord:
    metadata: dict[str, Any] = {}
    if o.receipt:
        metadata["receipt"] = o.receipt
    if o.notes:
        metadata["notes"] = o.notes

    return FinancialRecord(
        source=SourceType.RAZORPAY_TEST,
        record_type=RecordType.ORDER,
        external_id=o.id,
        amount=o.amount,
        currency=o.currency,
        status=o.status,
        transaction_at=_to_datetime(o.created_at),
        reference=o.receipt,
        description=f"Order {o.id}",
        metadata=metadata,
        raw_payload=o.raw,
        ingested_at=utcnow(),
        sync_run_id=sync_run_id,
        source_record_id=o.id,
    )


def map_settlement(s: RazorpaySettlement, sync_run_id: str) -> FinancialRecord:
    metadata: dict[str, Any] = {}
    if s.utr:
        metadata["utr"] = s.utr

    return FinancialRecord(
        source=SourceType.RAZORPAY_TEST,
        record_type=RecordType.SETTLEMENT,
        external_id=s.id,
        amount=s.amount,
        currency=s.currency,
        status=s.status,
        transaction_at=_to_datetime(s.created_at),
        reference=s.utr,
        description=f"Settlement {s.id}",
        metadata=metadata,
        raw_payload=s.raw,
        ingested_at=utcnow(),
        sync_run_id=sync_run_id,
        source_record_id=s.id,
    )


def map_recon_event(e: RazorpaySettlementReconEvent, sync_run_id: str) -> FinancialRecord:
    metadata: dict[str, Any] = {}
    if e.settlement_id:
        metadata["settlement_id"] = e.settlement_id
    if e.settlement_utr:
        metadata["utr"] = e.settlement_utr
    if e.type:
        metadata["type"] = e.type

    return FinancialRecord(
        source=SourceType.RAZORPAY_TEST,
        record_type=RecordType.RECON_EVENT,
        external_id=e.entity_id,
        amount=e.amount or 0,
        currency="INR",
        status="settled" if e.settled else "pending",
        transaction_at=_to_datetime(e.created_at),
        reference=e.settlement_id,
        description=f"Recon event {e.entity_type}",
        metadata=metadata,
        raw_payload=e.raw,
        ingested_at=utcnow(),
        sync_run_id=sync_run_id,
        source_record_id=e.entity_id,
    )

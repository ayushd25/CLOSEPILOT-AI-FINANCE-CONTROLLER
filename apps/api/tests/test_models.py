import pytest
from datetime import datetime, timedelta, timezone
from app.domain.models import FinancialRecord, RecordType, SourceType


def make_record(record_type=RecordType.PAYMENT, amount=10000, external_id="pay_1", reference="REF1", transaction_days_ago=5, **kwargs) -> FinancialRecord:
    ts = datetime.now(timezone.utc) - timedelta(days=transaction_days_ago)
    return FinancialRecord(
        source=SourceType.SYNTHETIC,
        record_type=record_type,
        external_id=external_id,
        amount=amount,
        currency="INR",
        status="settled",
        transaction_at=ts,
        reference=reference,
        metadata=kwargs.pop("metadata", {}),
    )


def test_financial_record_creation():
    rec = make_record()
    assert rec.record_type == RecordType.PAYMENT
    assert rec.amount == 10000
    assert rec.currency == "INR"


def test_financial_record_to_mongo_roundtrip():
    rec = make_record(reference="REF-123", metadata={"key": "value"})
    doc = rec.to_mongo()
    restored = FinancialRecord.from_mongo(doc)
    assert restored.amount == rec.amount
    assert restored.reference == "REF-123"
    assert restored.metadata == {"key": "value"}

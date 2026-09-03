import pytest
from datetime import datetime, timedelta, timezone

from app.domain.models import FinancialRecord, RecordType, SourceType
from app.evaluation.baselines import exact_id_baseline, amount_date_baseline


def _rec(record_type, external_id, amount, reference=None, transaction_at=None, metadata=None):
    return FinancialRecord(
        source=SourceType.SYNTHETIC,
        record_type=record_type,
        external_id=external_id,
        amount=amount,
        currency="INR",
        transaction_at=transaction_at or datetime.now(timezone.utc),
        reference=reference,
        metadata=metadata or {},
    )


def _group_records(records, case_num):
    return [FinancialRecord(**{**r.model_dump(), "external_id": f"{r.external_id}_{case_num}"}) for r in records]


def test_exact_id_baseline():
    ts = datetime.now(timezone.utc)
    pay = _rec(RecordType.PAYMENT, "pay_1", 10000, reference="INV_1")
    set = _rec(RecordType.SETTLEMENT, "set_1", 10000, reference="INV_1")
    records = [pay, set]

    ground_truth = {
        "SYN_CASE_1": {
            "case_id": "SYN_CASE_1",
            "expected_relationships": [
                {"from": "pay_1", "to": "set_1", "type": "MATCHED_TO"}
            ],
            "expected_outcome": "auto_resolve",
        }
    }

    pred = exact_id_baseline([pay, set], ground_truth)
    assert pred["SYN_CASE_1"]["matched"] is True


def test_amount_date_baseline():
    ts = datetime.now(timezone.utc)
    pay = _rec(RecordType.PAYMENT, "pay_1", 10000)
    set_ = _rec(RecordType.SETTLEMENT, "set_1", 10000, transaction_at=ts + timedelta(days=1))

    ground_truth = {
        "SYN_CASE_1": {
            "case_id": "SYN_CASE_1",
            "expected_relationships": [
                {"from": "pay_1", "to": "set_1", "type": "MATCHED_TO"}
            ],
            "expected_outcome": "auto_resolve",
        }
    }

    pred = amount_date_baseline([pay, set_], ground_truth)
    assert pred["SYN_CASE_1"]["matched"] is True

import pytest
from datetime import datetime, timedelta, timezone

from app.domain.models import FinancialRecord, RecordType, SourceType
from app.reconciliation.scoring import score_candidate, generate_candidates, detect_duplicate, similarity


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


def test_similarity_exact():
    assert similarity("INV_123", "INV_123") == 1.0


def test_similarity_typo():
    assert similarity("INV_123", "INV_124") > 0


def test_similarity_no_match():
    assert similarity("ABC", "XYZ") == 0.0


def test_exact_reference_scores_high():
    ts = datetime.now(timezone.utc)
    pay = _rec(RecordType.PAYMENT, "pay_1", 10000, reference="INV_100")
    set = _rec(RecordType.SETTLEMENT, "set_1", 10000, reference="INV_100", transaction_at=ts)
    score, triggered, signals = score_candidate(pay, set)
    assert score >= 160
    assert "exact_reference" in triggered
    assert "exact_amount" in triggered


def test_utr_match_scores_very_high():
    ts = datetime.now(timezone.utc)
    pay = _rec(RecordType.PAYMENT, "pay_1", 10000, metadata={"utr": "UTR123"})
    set = _rec(RecordType.SETTLEMENT, "set_1", 10000, metadata={"utr": "UTR123"}, transaction_at=ts)
    score, triggered, _ = score_candidate(pay, set)
    assert "utr_match" in triggered
    assert score >= 200


def test_amount_mismatch_lower_score():
    ts = datetime.now(timezone.utc)
    pay = _rec(RecordType.PAYMENT, "pay_1", 10000, reference="X")
    set = _rec(RecordType.SETTLEMENT, "set_1", 15000, reference="X", transaction_at=ts)
    score, _, _ = score_candidate(pay, set)
    assert score < 160


def test_generate_candidates_scales_to_bucket():
    ts = datetime.now(timezone.utc)
    records = []
    for i in range(100):
        rec = _rec(RecordType.SETTLEMENT, f"set_{i}", 10000 + i)
        records.append(rec)
    pay = _rec(RecordType.PAYMENT, "pay_1", 10000, reference="common")
    candidates = generate_candidates(pay, records + [pay])
    assert candidates  # finds some


def test_detect_duplicate():
    ts = datetime.now(timezone.utc)
    rec1 = _rec(RecordType.PAYMENT, "pay_1", 10000)
    rec2 = _rec(RecordType.PAYMENT, "pay_1", 10000, metadata={})
    assert detect_duplicate(rec1, [rec1, rec2])

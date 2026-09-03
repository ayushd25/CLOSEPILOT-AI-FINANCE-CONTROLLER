from datetime import timedelta
from typing import Any, Optional

from app.domain.cases import DeterministicInfo, OutcomeType, ReconciliationCase, RiskLevel
from app.domain.models import FinancialRecord, RecordType

DATE_TOLERANCE_DAYS = 3
AMOUNT_TOLERANCE = 100  # in minor units (₹1.00)
NORMALIZED_REF_TOLERANCE_DAYS = 5


def normalize_reference(ref: Optional[str]) -> str:
    if ref is None:
        return ""
    return str(ref).strip().lower().replace("-", "").replace("_", "")


def similarity(a: str, b: str) -> float:
    na, nb = normalize_reference(a), normalize_reference(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.8
    la, lb = len(na), len(nb)
    if max(la, lb) == 0:
        return 0.0
    commons = sum(1 for c in na if c in nb)
    return commons / max(la, lb)


def score_candidate(
    record: FinancialRecord,
    candidate: FinancialRecord,
) -> tuple[float, list[str], dict[str, Any]]:
    signals: dict[str, Any] = {}
    triggered: list[str] = []
    score = 0.0

    ref_score = similarity(record.reference or record.external_id, candidate.reference or candidate.external_id)
    if ref_score >= 1.0 and (record.reference or record.external_id) == (candidate.reference or candidate.external_id):
        score += 100
        triggered.append("exact_reference")
        signals["exact_reference"] = True
    elif ref_score >= 0.8:
        score += 50
        triggered.append("reference_similar")
        signals["reference_similarity"] = ref_score

    if record.amount == candidate.amount:
        score += 60
        triggered.append("exact_amount")
        signals["exact_amount"] = True
    elif abs(record.amount - candidate.amount) <= AMOUNT_TOLERANCE:
        score += 30
        triggered.append("amount_tolerance")
        signals["amount_tolerance"] = abs(record.amount - candidate.amount)

    if record.currency and candidate.currency and record.currency == candidate.currency:
        score += 20
        triggered.append("same_currency")
        signals["same_currency"] = record.currency

    if record.transaction_at and candidate.transaction_at:
        diff = abs((record.transaction_at - candidate.transaction_at).total_seconds())
        if diff <= timedelta(days=DATE_TOLERANCE_DAYS).total_seconds():
            score += 20
            triggered.append("date_proximity")
            signals["date_diff_seconds"] = diff

    rec_meta = record.metadata or {}
    cand_meta = candidate.metadata or {}
    utr_r = rec_meta.get("utr")
    utr_c = cand_meta.get("utr")
    if utr_r and utr_c and normalize_reference(str(utr_r)) == normalize_reference(str(utr_c)):
        score += 150
        triggered.append("utr_match")
        signals["utr_match"] = True

    return score, triggered, signals


def generate_candidates(
    record: FinancialRecord,
    all_records: list[FinancialRecord],
    max_candidates: int = 5,
) -> list[tuple[FinancialRecord, float, list[str], dict[str, Any]]]:
    candidates = []

    potential = [
        r for r in all_records
        if (r.id and r.id != record.id or not r.id and r.external_id != record.external_id)
        and r.record_type != record.record_type
        and r.currency == record.currency
    ]

    for cand in potential:
        score, triggered, signals = score_candidate(record, cand)
        if score > 0:
            candidates.append((cand, score, triggered, signals))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:max_candidates]


def detect_duplicate(record: FinancialRecord, same_type_records: list[FinancialRecord]) -> bool:
    seen: dict[tuple[str, str, str, int], int] = {}
    for other in same_type_records:
        if record.id and other.id and other.id == record.id:
            continue
        key = (other.external_id, other.record_type.value if hasattr(other.record_type, 'value') else str(other.record_type), other.currency, other.amount)
        seen[key] = seen.get(key, 0) + 1
    my_key = (record.external_id, record.record_type.value if hasattr(record.record_type, 'value') else str(record.record_type), record.currency, record.amount)
    return seen.get(my_key, 0) > 0

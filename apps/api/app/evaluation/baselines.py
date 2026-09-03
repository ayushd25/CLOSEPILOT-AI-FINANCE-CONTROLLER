from typing import Any

from app.domain.models import FinancialRecord


def _find_record(records: list[FinancialRecord], record_type: str, ref_external: str) -> FinancialRecord | None:
    for r in records:
        if r.external_id == ref_external:
            return r
    return None


def exact_id_baseline(records: list[FinancialRecord], ground_truth: dict) -> dict:
    predictions = {}

    for case_id, gt in ground_truth.items():
        expected_rel = gt.get("expected_relationships", [])
        matched = False

        for rel in expected_rel:
            from_rec = _find_record(records, rel.get("type", ""), rel["from"])
            to_rec = _find_record(records, rel.get("type", ""), rel["to"])
            if from_rec and to_rec:
                from_ref = from_rec.reference or from_rec.external_id
                to_ref = to_rec.reference or to_rec.external_id
                if from_ref == to_ref:
                    matched = True
                    break

        predictions[case_id] = {"matched": matched, "auto_close": matched}
    return predictions


def amount_date_baseline(records: list[FinancialRecord], ground_truth: dict) -> dict:
    from datetime import timedelta

    predictions = {}

    for case_id, gt in ground_truth.items():
        expected_rel = gt.get("expected_relationships", [])
        matched = False

        for rel in expected_rel:
            from_rec = _find_record(records, rel.get("type", ""), rel["from"])
            to_rec = _find_record(records, rel.get("type", ""), rel["to"])
            if from_rec and to_rec:
                amount_match = from_rec.amount == to_rec.amount
                date_match = True
                if from_rec.transaction_at and to_rec.transaction_at:
                    diff = abs((from_rec.transaction_at - to_rec.transaction_at).total_seconds())
                    date_match = diff <= timedelta(days=7).total_seconds()
                if amount_match and date_match:
                    matched = True
                    break

        predictions[case_id] = {"matched": matched, "auto_close": matched}
    return predictions


def fuzzy_baseline(records: list[FinancialRecord], ground_truth: dict) -> dict:
    from app.reconciliation.scoring import similarity

    predictions = {}

    for case_id, gt in ground_truth.items():
        expected_rel = gt.get("expected_relationships", [])
        matched = False

        for rel in expected_rel:
            from_rec = _find_record(records, rel.get("type", ""), rel["from"])
            to_rec = _find_record(records, rel.get("type", ""), rel["to"])
            if from_rec and to_rec:
                ref_sim = similarity(from_rec.reference or from_rec.description or "", to_rec.reference or to_rec.description or "")
                amt_sim = 1.0 if from_rec.amount == to_rec.amount else 0.5
                combined = 0.5 * ref_sim + 0.5 * amt_sim
                if combined >= 0.6:
                    matched = True
                    break

        predictions[case_id] = {"matched": matched, "auto_close": matched}
    return predictions

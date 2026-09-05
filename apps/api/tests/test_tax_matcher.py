from datetime import datetime, timedelta, timezone

from app.domain.models import FinancialRecord, RecordType, SourceType
from app.domain.tax_match import TaxMatchStatus
from app.reconciliation.tax_matcher import TaxLineMatcher
from app.synthetic.generator import DEFAULT_MIX, SCENARIO_CATALOG
from app.synthetic.random_util import get_seeded_rng
from app.synthetic.scenarios import generate_scenario


def _rec(rtype: RecordType, amount: int, reference=None, metadata=None, ext="") -> FinancialRecord:
    return FinancialRecord(
        source=SourceType.SYNTHETIC,
        record_type=rtype,
        external_id=ext,
        amount=amount,
        reference=reference,
        metadata=metadata or {},
        transaction_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        status="settled",
    )


def _line_from_scenario(scenario: str):
    rng = get_seeded_rng(7)
    case = generate_scenario(rng, scenario)
    recs = {r.record_type: r for r in case.records}
    return {
        "reference": recs[RecordType.PAYMENT].reference,
        "payment": recs[RecordType.PAYMENT],
        "settlement": recs[RecordType.SETTLEMENT],
        "tax": recs[RecordType.TAX],
        "invoice": recs.get(RecordType.INVOICE),
    }


def test_tax_line_match_is_verified():
    line = _line_from_scenario("tax_line_match")
    match = TaxLineMatcher._match_line(line)
    assert match.status == TaxMatchStatus.VERIFIED
    invoice = line["invoice"]
    taxable = invoice.metadata["taxable_amount"]
    rate = invoice.metadata["tax_rate"]
    assert match.expected_tax == round(taxable * rate / 100)
    assert match.recorded_tax == match.expected_tax
    assert match.difference == 0
    assert "rate_applied" in match.reason_codes
    assert f"× {rate}%" in match.calculation


def test_tax_line_mismatch_is_exception():
    line = _line_from_scenario("tax_line_mismatch")
    match = TaxLineMatcher._match_line(line)
    assert match.status == TaxMatchStatus.EXCEPTION
    assert "tax_rate_calculation_mismatch" in match.reason_codes
    assert abs(match.difference) > match.tolerance
    assert match.expected_tax != match.recorded_tax


def test_legacy_tax_gross_net_consistent_is_verified():
    # Legacy `tax` scenario: no rate metadata, payment = settlement + tax.
    gross, tax = 100_000, 12_000
    line = {
        "reference": None,
        "payment": _rec(RecordType.PAYMENT, gross, ext="pay_1"),
        "settlement": _rec(RecordType.SETTLEMENT, gross - tax, metadata={"tax": tax}, ext="set_1"),
        "tax": _rec(RecordType.TAX, tax, ext="tax_1"),
        "invoice": None,
    }
    match = TaxLineMatcher._match_line(line)
    assert match.status == TaxMatchStatus.VERIFIED
    assert match.expected_tax == tax


def test_missing_tax_line_is_human_review():
    payment = _rec(RecordType.PAYMENT, 50_000, ext="pay_1")
    line = {"reference": None, "payment": payment, "settlement": None, "tax": None, "invoice": None}
    match = TaxLineMatcher._match_line(line)
    assert match.status == TaxMatchStatus.HUMAN_REVIEW
    assert "missing_tax_line" in match.reason_codes
    assert match.confidence == 0.0


def test_build_lines_groups_by_reference():
    rng = get_seeded_rng(9)
    case1 = generate_scenario(rng, "tax_line_match")
    case2 = generate_scenario(rng, "tax_line_mismatch")
    records = case1.records + case2.records
    lines, skipped = TaxLineMatcher._build_lines(records)
    refs = {l["reference"] for l in lines}
    assert len(lines) == 2
    assert skipped == 0
    assert refs == {case1.records[0].reference, case2.records[0].reference}


def test_legacy_tax_scenario_is_reference_linked():
    rng = get_seeded_rng(11)
    case = generate_scenario(rng, "tax")
    refs = {r.reference for r in case.records}
    assert len(refs) == 1 and next(iter(refs))
    lines, skipped = TaxLineMatcher._build_lines(case.records)
    assert len(lines) == 1
    assert skipped == 0


def test_new_scenarios_in_catalog_and_default_mix():
    assert "tax_line_match" in SCENARIO_CATALOG
    assert "tax_line_mismatch" in SCENARIO_CATALOG
    assert DEFAULT_MIX["tax_line_match"] > 0
    assert DEFAULT_MIX["tax_line_mismatch"] > 0


async def test_tax_match_run_persists_and_links_cases():
    from app.db import Database

    db = Database.get_db()
    try:
        await db.command("ping")
    except Exception:
        import pytest
        pytest.skip("MongoDB not available; skipping integration test")

    for collection in ("financial_records", "reconciliation_cases", "tax_matches", "evidence_items", "audit_events"):
        await db[collection].delete_many({})

    from app.synthetic.generator import SyntheticDataSource

    gen = SyntheticDataSource()
    records, _, _ = await gen.generate(n_cases=20, seed=42, scenario_mix={
        "tax_line_match": 8,
        "tax_line_mismatch": 6,
        "tax": 6,
    })
    for rec in records:
        await db.financial_records.insert_one(rec.to_mongo())

    matcher = TaxLineMatcher()
    summary = await matcher.run(run_ai=False)
    assert summary["processed"] >= 14
    assert summary["verified"] > 0
    assert summary["exceptions"] > 0

    docs = await db.tax_matches.find({}).to_list(length=10000)
    assert len(docs) == summary["processed"]
    statuses = {d["status"] for d in docs}
    assert "VERIFIED" in statuses and "EXCEPTION" in statuses

    exceptions = [d for d in docs if d["status"] == "EXCEPTION"]
    for d in exceptions:
        assert d["case_id"], "exception should be linked to a case"
        case = await db.reconciliation_cases.find_one({"case_id": d["case_id"]})
        assert case, "linked case must exist"
        assert case["outcome_type"] == "tax_discrepancy"
        assert d["evidence_ids"], "exception should carry evidence"

    verified = [d for d in docs if d["status"] == "VERIFIED"]
    for d in verified:
        assert d["difference"] == 0
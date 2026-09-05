import random
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.models import FinancialRecord, RecordType, SourceType
from app.synthetic.random_util import get_seeded_rng, rand_amount_minor, random_id


class SyntheticCase:
    def __init__(
        self,
        scenario: str,
        records: list[FinancialRecord],
        ground_truth: dict[str, Any],
    ):
        self.scenario = scenario
        self.records = records
        self.ground_truth = ground_truth


def _make_record(rng: random.Random, record_type: RecordType, external_id: str, amount: int, **kwargs) -> FinancialRecord:
    now = kwargs.pop("transaction_at", datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30)))
    metadata = kwargs.pop("metadata", {})
    return FinancialRecord(
        source=SourceType.SYNTHETIC,
        record_type=record_type,
        external_id=external_id,
        amount=amount,
        currency=kwargs.pop("currency", "INR"),
        status=kwargs.pop("status", "settled"),
        transaction_at=now,
        reference=kwargs.pop("reference", None),
        description=kwargs.pop("description", f"{record_type.value} {external_id}"),
        metadata=metadata,
        raw_payload={"scenario": "synthetic"},
    )


def generate_scenario(rng: random.Random, scenario: str) -> SyntheticCase:
    if scenario == "exact_match":
        return _exact_match(rng)
    if scenario == "reference_match":
        return _reference_match(rng)
    if scenario == "amount_match":
        return _amount_match(rng)
    if scenario == "fee_deduction":
        return _fee_deduction(rng)
    if scenario == "tax":
        return _tax(rng)
    if scenario == "tax_line_match":
        return _tax_line(rng, mismatch=False)
    if scenario == "tax_line_mismatch":
        return _tax_line(rng, mismatch=True)
    if scenario == "date_drift":
        return _date_drift(rng)
    if scenario == "reference_typo":
        return _reference_typo(rng)
    if scenario == "missing_settlement":
        return _missing_settlement(rng)
    if scenario == "missing_bank_transaction":
        return _missing_bank(rng)
    if scenario == "duplicate":
        return _duplicate(rng)
    if scenario == "partial_settlement":
        return _partial(rng)
    if scenario == "split_settlement":
        return _split(rng)
    if scenario == "refund":
        return _refund(rng)
    if scenario == "chargeback":
        return _chargeback(rng)
    if scenario == "adjustment":
        return _adjustment(rng)
    if scenario == "multiple_candidates":
        return _multiple_candidates(rng)
    if scenario == "conflicting_evidence":
        return _conflicting(rng)
    if scenario == "amount_mismatch":
        return _amount_mismatch(rng)
    if scenario == "suspicious":
        return _suspicious(rng)
    if scenario == "unresolvable":
        return _unresolvable(rng)
    return _exact_match(rng)


def _exact_match(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ref = f"PAY_{rng.randint(10000, 99999)}"
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, reference=ref, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt, reference=ref, transaction_at=ts + timedelta(days=2), metadata={"utr": f"UTR{rng.randint(100000000, 999999999)}"})
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt, reference=ref, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "exact_match",
        [payment, settlement, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "auto_resolve",
            "expected_auto_or_human": "auto",
        },
    )


def _reference_match(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ref = f"INV_{rng.randint(10000, 99999)}"
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, reference=ref, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt, reference=ref, transaction_at=ts + timedelta(days=1))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt, reference=ref, transaction_at=ts + timedelta(days=1))

    return SyntheticCase(
        "reference_match",
        [payment, settlement, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "auto_resolve",
            "expected_auto_or_human": "auto",
        },
    )


def _amount_match(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt, transaction_at=ts + timedelta(days=2))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "amount_match",
        [payment, settlement, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "auto_resolve",
            "expected_auto_or_human": "auto",
        },
    )


def _fee_deduction(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    fee = rng.randint(100, 500) * 100
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt - fee, transaction_at=ts + timedelta(days=1), metadata={"fee": fee})
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt - fee, transaction_at=ts + timedelta(days=1))

    fee_record = _make_record(rng, RecordType.FEE, f"fee_{rng.randint(100000, 999999)}", fee, transaction_at=ts + timedelta(days=1))

    return SyntheticCase(
        "fee_deduction",
        [payment, settlement, bank, fee_record],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "auto_resolve",
            "expected_auto_or_human": "auto",
        },
    )


def _tax(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    tax = rng.randint(100, 200) * 100
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))
    ref = f"TAX_{rng.randint(100000, 999999)}"

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, reference=ref, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt - tax, reference=ref, transaction_at=ts + timedelta(days=1), metadata={"tax": tax})
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt - tax, reference=ref, transaction_at=ts + timedelta(days=1))

    tax_record = _make_record(rng, RecordType.TAX, f"tax_{rng.randint(100000, 999999)}", tax, reference=ref, transaction_at=ts + timedelta(days=1))

    return SyntheticCase(
        "tax",
        [payment, settlement, bank, tax_record],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "auto_resolve",
            "expected_auto_or_human": "auto",
        },
    )


def _tax_line(rng: random.Random, mismatch: bool) -> SyntheticCase:
    """Invoice-driven tax line with an explicit taxable amount + GST rate.

    Deterministic invariant: expected_tax = round(taxable_amount * tax_rate / 100).
    - tax_line_match:    the gateway's recorded tax equals the expected tax.
    - tax_line_mismatch: the gateway recorded a different tax (TAX_DISCREPANCY).
    """
    taxable = rand_amount_minor(rng)
    rate = rng.choice([5, 12, 18, 28])
    expected_tax = int(round(taxable * rate / 100))
    if mismatch:
        recorded_tax = expected_tax + rng.choice([-1, 1]) * (rng.randint(100, 500) * 100)
    else:
        recorded_tax = expected_tax
    fee = rng.choice([0, rng.randint(100, 300) * 100])
    gross = taxable + expected_tax
    net = gross - recorded_tax - fee
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))
    ref = f"INV_{rng.randint(10000, 99999)}"

    inv_id = f"inv_{rng.randint(100000, 999999)}"
    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    tax_id = f"tax_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    tax_meta = {"tax_rate": rate, "taxable_amount": taxable}
    invoice = _make_record(
        rng, RecordType.INVOICE, inv_id, gross, reference=ref,
        transaction_at=ts, metadata=tax_meta, description=f"Invoice {ref}",
    )
    payment = _make_record(
        rng, RecordType.PAYMENT, pay_id, gross, reference=ref,
        transaction_at=ts, metadata=tax_meta,
    )
    settlement = _make_record(
        rng, RecordType.SETTLEMENT, set_id, net, reference=ref,
        transaction_at=ts + timedelta(days=1),
        metadata={"tax": recorded_tax, "fee": fee},
    )
    tax_record = _make_record(
        rng, RecordType.TAX, tax_id, recorded_tax, reference=ref,
        transaction_at=ts + timedelta(days=1), metadata=tax_meta,
    )
    bank = _make_record(
        rng, RecordType.BANK_TRANSACTION, bank_id, net, reference=ref,
        transaction_at=ts + timedelta(days=1),
    )

    return SyntheticCase(
        "tax_line_mismatch" if mismatch else "tax_line_match",
        [invoice, payment, settlement, tax_record, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "exception" if mismatch else "auto_resolve",
            "expected_auto_or_human": "human" if mismatch else "auto",
        },
    )


def _date_drift(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(30, 60))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt, transaction_at=ts + timedelta(days=10))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt, transaction_at=ts + timedelta(days=10))

    return SyntheticCase(
        "date_drift",
        [payment, settlement, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _reference_typo(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ref = f"INV_{rng.randint(10000, 99999)}"
    ref_typo = ref[:-1] + ("0" if ref[-1] != "0" else "1")
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, reference=ref, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt, reference=ref_typo, transaction_at=ts + timedelta(days=1))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt, reference=ref, transaction_at=ts + timedelta(days=1))

    return SyntheticCase(
        "reference_typo",
        [payment, settlement, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "investigate",
            "expected_auto_or_human": "human",
        },
    )


def _missing_settlement(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)

    return SyntheticCase(
        "missing_settlement",
        [payment],
        {
            "expected_relationships": [],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _missing_bank(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "missing_bank_transaction",
        [payment, settlement],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
            ],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _duplicate(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    dup_id = f"pay_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    duplicate = _make_record(rng, RecordType.PAYMENT, dup_id, amt, transaction_at=ts)

    return SyntheticCase(
        "duplicate",
        [payment, duplicate],
        {
            "expected_relationships": [],
            "expected_outcome": "duplicate",
            "expected_auto_or_human": "human",
        },
    )


def _partial(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    partial = amt // 2
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, partial, transaction_at=ts + timedelta(days=2))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, partial, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "partial_settlement",
        [payment, settlement, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _split(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    half = amt // 2
    remainder = amt - half
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set1 = f"set_{rng.randint(100000, 999999)}"
    set2 = f"set_{rng.randint(100000, 999999)}"
    bank1 = f"bank_{rng.randint(100000, 999999)}"
    bank2 = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement1 = _make_record(rng, RecordType.SETTLEMENT, set1, half, transaction_at=ts + timedelta(days=1))
    settlement2 = _make_record(rng, RecordType.SETTLEMENT, set2, remainder, transaction_at=ts + timedelta(days=2))
    bank1_r = _make_record(rng, RecordType.BANK_TRANSACTION, bank1, half, transaction_at=ts + timedelta(days=1))
    bank2_r = _make_record(rng, RecordType.BANK_TRANSACTION, bank2, remainder, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "split_settlement",
        [payment, settlement1, settlement2, bank1_r, bank2_r],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set1, "type": "MATCHED_TO"},
                {"from": pay_id, "to": set2, "type": "MATCHED_TO"},
                {"from": set1, "to": bank1, "type": "SETTLED_AS"},
                {"from": set2, "to": bank2, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _refund(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    refund_amt = amt // 2
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"
    refund_id = f"rfnd_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt - refund_amt, transaction_at=ts + timedelta(days=2))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt - refund_amt, transaction_at=ts + timedelta(days=2))
    refund = _make_record(rng, RecordType.REFUND, refund_id, refund_amt, transaction_at=ts + timedelta(days=1))

    return SyntheticCase(
        "refund",
        [payment, settlement, bank, refund],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
                {"from": pay_id, "to": refund_id, "type": "REFUNDED_BY"},
            ],
            "expected_outcome": "auto_resolve",
            "expected_auto_or_human": "auto",
        },
    )


def _chargeback(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    cb_id = f"cb_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, -amt, transaction_at=ts + timedelta(days=5))
    chargeback = _make_record(rng, RecordType.CHARGEBACK, cb_id, amt, transaction_at=ts + timedelta(days=4))

    return SyntheticCase(
        "chargeback",
        [payment, settlement, chargeback],
        {
            "expected_relationships": [
                {"from": pay_id, "to": cb_id, "type": "CONFLICTS_WITH"},
            ],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _adjustment(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    adj_amt = rng.randint(100, 500) * 100
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    adj_id = f"adj_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt - adj_amt, transaction_at=ts + timedelta(days=2))
    adjustment = _make_record(rng, RecordType.ADJUSTMENT, adj_id, -adj_amt, transaction_at=ts + timedelta(days=1))

    return SyntheticCase(
        "adjustment",
        [payment, settlement, adjustment],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": adj_id, "type": "ADJUSTED_BY"},
            ],
            "expected_outcome": "auto_resolve",
            "expected_auto_or_human": "auto",
        },
    )


def _multiple_candidates(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set1 = f"set_{rng.randint(100000, 999999)}"
    set2 = f"set_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    s1 = _make_record(rng, RecordType.SETTLEMENT, set1, amt, transaction_at=ts + timedelta(days=2))
    s2 = _make_record(rng, RecordType.SETTLEMENT, set2, amt, transaction_at=ts + timedelta(days=3))

    return SyntheticCase(
        "multiple_candidates",
        [payment, s1, s2],
        {
            "expected_relationships": [],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _conflicting(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set1 = f"set_{rng.randint(100000, 999999)}"
    set2 = f"set_{rng.randint(100000, 999999)}"
    bank1 = f"bank_{rng.randint(100000, 999999)}"
    bank2 = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    s1 = _make_record(rng, RecordType.SETTLEMENT, set1, amt, transaction_at=ts + timedelta(days=2))
    s2 = _make_record(rng, RecordType.SETTLEMENT, set2, amt, transaction_at=ts + timedelta(days=2), metadata={"utr": "UTR_DIFFERENT"})
    b1 = _make_record(rng, RecordType.BANK_TRANSACTION, bank1, amt, transaction_at=ts + timedelta(days=2))
    b2 = _make_record(rng, RecordType.BANK_TRANSACTION, bank2, amt, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "conflicting_evidence",
        [payment, s1, s2, b1, b2],
        {
            "expected_relationships": [],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _amount_mismatch(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    mismatch = amt - rng.randint(500, 2000) * 100
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts)
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, mismatch, transaction_at=ts + timedelta(days=2))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, mismatch, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "amount_mismatch",
        [payment, settlement, bank],
        {
            "expected_relationships": [
                {"from": pay_id, "to": set_id, "type": "MATCHED_TO"},
                {"from": set_id, "to": bank_id, "type": "SETTLED_AS"},
            ],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _suspicious(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts, description="URGENT!! verify immediately")
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, amt + rng.randint(1000, 5000) * 100, transaction_at=ts + timedelta(days=2))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, amt + rng.randint(1000, 5000) * 100, transaction_at=ts + timedelta(days=2))

    return SyntheticCase(
        "suspicious",
        [payment, settlement, bank],
        {
            "expected_relationships": [],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )


def _unresolvable(rng: random.Random) -> SyntheticCase:
    amt = rand_amount_minor(rng)
    other_amt = amt + rng.randint(5000, 10000) * 100
    ts = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))

    pay_id = f"pay_{rng.randint(100000, 999999)}"
    set_id = f"set_{rng.randint(100000, 999999)}"
    bank_id = f"bank_{rng.randint(100000, 999999)}"

    payment = _make_record(rng, RecordType.PAYMENT, pay_id, amt, transaction_at=ts, description="")
    settlement = _make_record(rng, RecordType.SETTLEMENT, set_id, other_amt, transaction_at=ts + timedelta(days=20))
    bank = _make_record(rng, RecordType.BANK_TRANSACTION, bank_id, other_amt, transaction_at=ts + timedelta(days=20))

    return SyntheticCase(
        "unresolvable",
        [payment, settlement, bank],
        {
            "expected_relationships": [],
            "expected_outcome": "exception",
            "expected_auto_or_human": "human",
        },
    )

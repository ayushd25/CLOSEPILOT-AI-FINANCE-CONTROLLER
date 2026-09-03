import pytest

from app.synthetic.scenarios import generate_scenario
from app.synthetic.random_util import get_seeded_rng
from app.synthetic.generator import SCENARIO_CATALOG
from app.domain.models import RecordType


@pytest.mark.parametrize("scenario", SCENARIO_CATALOG)
def test_scenario_generation(scenario):
    rng = get_seeded_rng(42)
    case = generate_scenario(rng, scenario)
    assert case.scenario == scenario
    assert len(case.records) > 0
    assert case.ground_truth.get("expected_outcome") in ("auto_resolve", "exception", "investigate", "duplicate")


def test_seeded_reproducibility():
    rng1 = get_seeded_rng(123)
    rng2 = get_seeded_rng(123)
    case1 = generate_scenario(rng1, "exact_match")
    case2 = generate_scenario(rng2, "exact_match")
    assert [r.external_id for r in case1.records] == [r.external_id for r in case2.records]


def test_scenario_has_three_source_records():
    rng = get_seeded_rng(42)
    case = generate_scenario(rng, "exact_match")
    types = [r.record_type for r in case.records]
    assert RecordType.PAYMENT in types
    assert RecordType.SETTLEMENT in types
    assert RecordType.BANK_TRANSACTION in types


def test_fee_deduction_scenario():
    rng = get_seeded_rng(42)
    case = generate_scenario(rng, "fee_deduction")
    payment = next(r for r in case.records if r.record_type == RecordType.PAYMENT)
    settlement = next(r for r in case.records if r.record_type == RecordType.SETTLEMENT)
    fee = settlement.metadata.get("fee")
    assert fee and fee > 0
    assert settlement.amount == payment.amount - fee


def test_duplicate_scenario():
    rng = get_seeded_rng(42)
    case = generate_scenario(rng, "duplicate")
    assert case.ground_truth["expected_outcome"] == "duplicate"
    payments = [r for r in case.records if r.record_type == RecordType.PAYMENT]
    assert len(payments) == 2

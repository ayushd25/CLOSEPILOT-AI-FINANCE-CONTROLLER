from datetime import datetime, timedelta, timezone

from app.domain.cases import CaseStatus, ReconciliationCase
from app.domain.forecast import CashForecast
from app.domain.models import FinancialRecord, RecordType, SourceType
from app.forecast.service import ForwardCashForecaster


def _record(record_type: RecordType, amount: int, ts: datetime, external_id: str = "", currency: str = "INR") -> FinancialRecord:
    return FinancialRecord(
        source=SourceType.SYNTHETIC,
        record_type=record_type,
        external_id=external_id,
        amount=amount,
        currency=currency,
        transaction_at=ts,
        status="settled",
    )


def _as_of() -> datetime:
    return datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def _steady_history(days: int = 30, daily: int = 100_000) -> list[FinancialRecord]:
    """One payment + settlement + bank per day, settled next day."""
    records = []
    as_of = _as_of()
    for i in range(1, days + 1):
        ts = as_of - timedelta(days=days - i + 1)
        pay = _record(RecordType.PAYMENT, daily, ts, external_id=f"pay_{i}")
        set_ts = ts + timedelta(days=1)
        settlement = _record(RecordType.SETTLEMENT, daily, set_ts, external_id=f"set_{i}")
        bank = _record(RecordType.BANK_TRANSACTION, daily, set_ts, external_id=f"bank_{i}")
        records += [pay, settlement, bank]
    return records


def test_compute_empty_inputs():
    f = ForwardCashForecaster.compute([], [], horizon_days=7, as_of=_as_of())
    assert isinstance(f, CashForecast)
    assert f.current_cash == 0
    assert f.projected_cash == 0
    assert len(f.points) == 7
    assert 0.1 <= f.confidence <= 0.95


def test_current_cash_from_bank_records():
    as_of = _as_of()
    records = [
        _record(RecordType.BANK_TRANSACTION, 5000, as_of - timedelta(days=2), "bank_1"),
        _record(RecordType.BANK_TRANSACTION, 3000, as_of - timedelta(days=1), "bank_2"),
        _record(RecordType.BANK_TRANSACTION, 4000, as_of + timedelta(days=1), "bank_future"),
    ]
    f = ForwardCashForecaster.compute(records, [], horizon_days=7, as_of=as_of)
    assert f.current_cash == 8000  # future bank record not counted yet


def test_scheduled_settlements_are_part_of_inflow():
    as_of = _as_of()
    records = _steady_history(days=10)
    records.append(_record(RecordType.SETTLEMENT, 90_000, as_of + timedelta(days=3), "set_future"))
    f = ForwardCashForecaster.compute(records, [], horizon_days=7, as_of=as_of)
    scheduled = next(c for c in f.components if c.category == "SCHEDULED_SETTLEMENTS")
    assert scheduled.amount == 90_000
    assert f.inflow_expected >= 90_000


def test_risk_holdback_reduces_projected_cash():
    as_of = _as_of()
    records = _steady_history(days=30)
    open_case = ReconciliationCase(
        case_id="CASE_pay_1",
        status=CaseStatus.EXCEPTION,
        amount=50_000,
        record_type="payment",
    )
    resolved_case = ReconciliationCase(
        case_id="CASE_pay_2",
        status=CaseStatus.AUTO_RESOLVED,
        amount=999_999,
        record_type="payment",
    )
    f = ForwardCashForecaster.compute(records, [open_case, resolved_case], horizon_days=7, as_of=as_of)
    assert f.risk_holdback == 50_000
    assert f.projected_cash == f.projected_optimistic - 50_000

    risk = next(c for c in f.components if c.category == "RISK_HOLDBACK")
    assert risk.amount == 50_000
    assert risk.count == 1


def test_curve_points_match_horizon_and_start_from_current_cash():
    as_of = _as_of()
    records = _steady_history(days=30, daily=100_000)
    f = ForwardCashForecaster.compute(records, [], horizon_days=14, as_of=as_of)
    assert len(f.points) == 14
    assert f.points[-1].projected_cash == f.current_cash + f.net_change
    assert f.points[0].projected_cash > f.current_cash  # day 1 already includes the first step
    assert all(p.lower_bound <= p.projected_cash <= p.upper_bound for p in f.points)


def test_invalid_horizon_falls_back_to_seven():
    records = _steady_history(days=30)
    f = ForwardCashForecaster.compute(records, [], horizon_days=99, as_of=_as_of())
    assert f.horizon_days == 7


def test_feet_tax_component_is_flagged_netted():
    as_of = _as_of()
    records = _steady_history(days=30, daily=100_000)
    records.append(_record(RecordType.FEE, 1_800, as_of - timedelta(days=1), "fee_1"))
    records.append(_record(RecordType.TAX, 18_000, as_of - timedelta(days=1), "tax_1"))
    f = ForwardCashForecaster.compute(records, [], horizon_days=7, as_of=as_of)
    gateway = [c for c in f.components if c.category == "GATEWAY_FEES_AND_TAX"]
    assert gateway and gateway[0].netted is True


def test_confidence_reflects_history_and_open_cases():
    as_of = _as_of()
    thin = ForwardCashForecaster.compute(_steady_history(days=3), [], 7, as_of=as_of)
    rich = ForwardCashForecaster.compute(_steady_history(days=60), [], 7, as_of=as_of)
    assert rich.confidence >= thin.confidence

    open_case = ReconciliationCase(case_id="CASE_x", status=CaseStatus.HUMAN_REVIEW, amount=10_000, record_type="payment")
    rich_with_risk = ForwardCashForecaster.compute(_steady_history(days=60), [open_case], 7, as_of=as_of)
    assert rich_with_risk.confidence <= rich.confidence

    assert 0.1 <= thin.confidence <= 0.95
    assert round(thin.confidence, 2) == thin.confidence


def test_deterministic_fallback_commentary():
    as_of = _as_of()
    f = ForwardCashForecaster.compute(_steady_history(days=30), [], 7, as_of=as_of)
    text = ForwardCashForecaster._fallback_commentary(f)
    assert "deterministic projection" in text.lower()
    assert str(f.horizon_days) in text
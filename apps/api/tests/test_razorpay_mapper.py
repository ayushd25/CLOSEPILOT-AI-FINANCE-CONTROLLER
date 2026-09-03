import pytest
from datetime import datetime, timezone

from app.integrations.razorpay.mapper import map_payment, map_settlement
from app.integrations.razorpay.models import RazorpayPayment, RazorpaySettlement


def test_map_payment():
    p = RazorpayPayment(
        id="pay_123",
        amount=10000,
        currency="INR",
        status="captured",
        method="card",
        order_id="order_1",
        captured=True,
        created_at=1700000000,
        raw={"id": "pay_123"},
    )
    rec = map_payment(p, "sync_1")
    assert rec.record_type == "payment"
    assert rec.external_id == "pay_123"
    assert rec.amount == 10000
    assert rec.source == "razorpay_test"
    assert rec.metadata["order_id"] == "order_1"


def test_map_settlement():
    s = RazorpaySettlement(
        id="set_1",
        amount=5000,
        status="settled",
        utr="UTR123",
        created_at=1700000000,
        raw={},
    )
    rec = map_settlement(s, "sync_1")
    assert rec.external_id == "set_1"
    assert rec.metadata["utr"] == "UTR123"

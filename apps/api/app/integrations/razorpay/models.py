from typing import Any, Optional

from pydantic import BaseModel


class RazorpayPayment(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    method: str
    order_id: Optional[str] = None
    captured: bool = True
    created_at: int
    notes: Optional[dict] = None
    description: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    fee: Optional[int] = None
    tax: Optional[int] = None
    raw: dict[str, Any]


class RazorpayOrder(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    receipt: Optional[str] = None
    created_at: int
    notes: Optional[dict] = None
    raw: dict[str, Any]


class RazorpaySettlement(BaseModel):
    id: str
    amount: int
    status: str
    currency: str = "INR"
    fees: Optional[int] = None
    tax: Optional[int] = None
    utr: Optional[str] = None
    created_at: int
    raw: dict[str, Any]


class RazorpaySettlementReconEvent(BaseModel):
    entity_id: str
    entity_type: str
    settlement_id: Optional[str] = None
    amount: Optional[int] = None
    fee: Optional[int] = None
    tax: Optional[int] = None
    on_hold: Optional[bool] = None
    settled: Optional[bool] = None
    created_at: Optional[int] = None
    settlement_utr: Optional[str] = None
    type: Optional[str] = None
    raw: dict[str, Any]

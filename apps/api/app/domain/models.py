from datetime import datetime

from app.utils import utcnow
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    SYNTHETIC = "synthetic"
    SYSTEM_CALCULATION = "system_calculation"
    HUMAN = "human"


class RecordType(str, Enum):
    PAYMENT = "payment"
    ORDER = "order"
    SETTLEMENT = "settlement"
    RECON_EVENT = "recon_event"
    BANK_TRANSACTION = "bank_transaction"
    INVOICE = "invoice"
    FEE = "fee"
    TAX = "tax"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    ADJUSTMENT = "adjustment"


class SourceInfo(BaseModel):
    type: SourceType
    source_record_id: str


class FinancialRecord(BaseModel):
    id: str = Field(default_factory=lambda: "")
    source: SourceType
    record_type: RecordType
    external_id: str
    account_id: str = "default"
    amount: int = 0
    currency: str = "INR"
    status: str = "unknown"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    transaction_at: Optional[datetime] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload: Optional[dict[str, Any]] = None
    ingested_at: datetime = Field(default_factory=utcnow)
    source_record_id: Optional[str] = None

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude_none=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "FinancialRecord":
        if "_id" in doc and "id" not in doc or (doc.get("id") == "" and "_id" in doc):
            doc["id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)

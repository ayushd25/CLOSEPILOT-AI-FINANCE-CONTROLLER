from datetime import datetime

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.utils import utcnow


class TaxMatchStatus(str, Enum):
    VERIFIED = "VERIFIED"
    EXCEPTION = "EXCEPTION"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class TaxMatch(BaseModel):
    match_id: str = ""
    tax_line_id: Optional[str] = None
    reference: Optional[str] = None
    transaction_id: str = ""
    invoice_id: Optional[str] = None
    currency: str = "INR"

    gross_amount: int = 0
    taxable_amount: int = 0
    tax_rate: Optional[int] = None  # percent
    expected_tax: int = 0
    recorded_tax: int = 0
    difference: int = 0
    tolerance: int = 0
    fee_amount: int = 0

    status: TaxMatchStatus = TaxMatchStatus.HUMAN_REVIEW
    reason_codes: list[str] = Field(default_factory=list)
    calculation: str = ""
    related_record_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    case_id: Optional[str] = None
    ai_analysis: Optional[str] = None
    confidence: float = 0.0

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None

    def to_mongo(self) -> dict:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_mongo(cls, doc: dict) -> "TaxMatch":
        if "_id" in doc and (doc.get("match_id") in (None, "")):
            doc["match_id"] = str(doc["_id"])
        if "_id" in doc:
            doc.pop("_id", None)
        return cls(**doc)
from datetime import datetime

from typing import Any, Optional

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    """One day on the forecast curve. Amounts are in minor units (paise)."""

    date: str
    projected_cash: int
    risk_adjusted_cash: int
    lower_bound: int
    upper_bound: int


class ForecastComponent(BaseModel):
    """A deterministic building block of the forecast."""

    category: str
    label: str
    amount: int
    count: int = 0
    detail: str = ""
    netted: bool = False


class ForecastDataQuality(BaseModel):
    days_of_history: int = 0
    records_used: dict[str, int] = Field(default_factory=dict)
    settlement_lag_days: int = 0
    refund_rate: float = 0.0
    avg_daily_settlement: int = 0
    daily_volatility: int = 0


class CashForecast(BaseModel):
    as_of: datetime
    horizon_days: int
    currency: str = "INR"

    current_cash: int = 0
    inflow_expected: int = 0
    outflow_expected: int = 0
    risk_holdback: int = 0
    net_change: int = 0
    projected_optimistic: int = 0
    projected_cash: int = 0

    confidence: float = 0.0
    data_quality: ForecastDataQuality = Field(default_factory=ForecastDataQuality)
    components: list[ForecastComponent] = Field(default_factory=list)
    points: list[ForecastPoint] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    commentary: Optional[str] = None

    def to_mongo(self) -> dict:
        return self.model_dump(mode="json")
from fastapi import APIRouter, Query

from app.forecast.service import VALID_HORIZONS, ForwardCashForecaster

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("")
async def get_forecast(
    horizon: int = Query(7, ge=1, le=90),
    ai: bool = Query(True, description="Whether to include AI commentary on the deterministic figures"),
):
    """Forward cash forecast: current cash + 7/14/30-day projection.

    Every number is computed deterministically from the financial records.
    When ``ai=true`` (and a GROQ key is configured) the model only *explains*
    the computed figures; it never invents numbers.
    """
    if horizon not in VALID_HORIZONS:
        horizon = 7
    forecaster = ForwardCashForecaster()
    forecast = await forecaster.build(horizon_days=horizon, use_ai=ai)
    return forecast.to_mongo()
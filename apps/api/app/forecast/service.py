"""Forward Cash Forecaster.

Deterministic, data-driven cash forecasting. The forecaster never lets an LLM
invent numbers: every cash figure on the curve is derived from the financial
records the platform already loaded (current bank cash, scheduled/estimated
settlements, receivables, refunds, chargebacks and adjustments). The AI (when
configured) is only allowed to *explain* the computed figures, never to change
them, keeping with ClosePilot's "models investigate, rules authorize" rule.
"""

import asyncio
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.db import Database
from app.domain.cases import ReconciliationCase
from app.domain.forecast import CashForecast, ForecastComponent, ForecastDataQuality, ForecastPoint
from app.domain.models import FinancialRecord, RecordType
from app.utils import utcnow

VALID_HORIZONS = (7, 14, 30)
HISTORY_DAYS = 60
AMOUNT_TOLERANCE = 100  # minor units: exact match tolerance used for linking


def _norm_ts(ts: Optional[datetime]) -> Optional[datetime]:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


class ForwardCashForecaster:
    def __init__(self):
        self.db = Database.get_db()

    # ------------------------------------------------------------------ #
    # Pure deterministic computation (unit-testable, no I/O)             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def compute(
        records: list[FinancialRecord],
        cases: Optional[list[ReconciliationCase]] = None,
        horizon_days: int = 7,
        as_of: Optional[datetime] = None,
    ) -> CashForecast:
        cases = cases or []
        as_of = _norm_ts(as_of) or utcnow()
        if horizon_days not in VALID_HORIZONS:
            horizon_days = 7

        currency = records[0].currency if records else "INR"
        floor = as_of - timedelta(days=HISTORY_DAYS)
        horizon_end = as_of + timedelta(days=horizon_days)

        banks = [r for r in records if r.record_type == RecordType.BANK_TRANSACTION]
        payments = [r for r in records if r.record_type == RecordType.PAYMENT]
        settlements = [
            r for r in records
            if r.record_type == RecordType.SETTLEMENT and r.amount > 0
        ]
        negative_settlements = [
            r for r in records
            if r.record_type == RecordType.SETTLEMENT and r.amount < 0
        ]
        refunds = [r for r in records if r.record_type == RecordType.REFUND]
        adjustments = [r for r in records if r.record_type == RecordType.ADJUSTMENT]

        # --- Current cash: settled money actually in the bank. ---------- #
        current_cash = sum(
            r.amount for r in banks if (_norm_ts(r.transaction_at) or as_of) <= as_of
        )

        # --- Historical daily net settlement (history window). ---------- #
        history_settlements = [
            r for r in settlements
            if floor <= (_norm_ts(r.transaction_at) or as_of) <= as_of
        ]
        daily: dict[date, int] = {}
        for r in history_settlements:
            day = (_norm_ts(r.transaction_at) or as_of).date()
            daily[day] = daily.get(day, 0) + r.amount
        days_of_history = len(daily)
        total_history = sum(daily.values())
        avg_daily_settlement = round(total_history / max(1, days_of_history))

        # Daily net cash motion (settlements minus refunds minus adjustments
        # minus negative settlements) for volatility banding.
        history_motion: dict[date, int] = {}
        for r in settlements + refunds + adjustments + negative_settlements:
            day = (_norm_ts(r.transaction_at) or as_of).date()
            if not (floor.date() <= day <= as_of.date()):
                continue
            history_motion[day] = history_motion.get(day, 0) + r.amount
        motion_values = list(history_motion.values())
        daily_volatility = round(
            int(statistics.pstdev(motion_values)) if len(motion_values) >= 2 else 0
        )
        if daily_volatility == 0 and avg_daily_settlement:
            daily_volatility = round(avg_daily_settlement * 0.1)

        # --- Refund rate from actual history. --------------------------- #
        gross_history = sum(r.amount for r in payments if (floor <= (_norm_ts(r.transaction_at) or as_of) <= as_of))
        refund_history = sum(r.amount for r in refunds if (floor <= (_norm_ts(r.transaction_at) or as_of) <= as_of))
        refund_rate = round(refund_history / gross_history, 4) if gross_history else 0.0

        # --- Settlement lag: median payment -> settlement gap. ---------- #
        lags: list[float] = []
        for p in payments:
            p_ts = _norm_ts(p.transaction_at) or as_of
            best = None
            for s in settlements:
                s_ts = _norm_ts(s.transaction_at) or as_of
                gap = (s_ts - p_ts).total_seconds() / 86400.0
                if 0 <= gap <= 10 and abs(s.amount - p.amount) <= AMOUNT_TOLERANCE:
                    if best is None or gap < best:
                        best = gap
            if best is not None:
                lags.append(best)
        lag_days = round(int(statistics.median(lags))) if lags else 2

        # --- Components. ------------------------------------------------ #
        components: list[ForecastComponent] = []

        # 1. Scheduled settlements: actual future settlement records.
        scheduled = [
            r for r in settlements
            if as_of < (_norm_ts(r.transaction_at) or as_of) <= horizon_end
        ]
        scheduled_amount = sum(r.amount for r in scheduled)

        # 2. Receivables: payments expected to settle within the horizon
        #    (still unpaid as of today, based on the observed settlement lag).
        receivables = []
        for p in payments:
            p_ts = _norm_ts(p.transaction_at) or as_of
            if p_ts <= as_of - timedelta(days=lag_days):
                continue
            # A payment is a receivable only if no bank credit has covered it yet.
            covered = any(
                r.amount == p.amount and as_of < (_norm_ts(r.transaction_at) or as_of) <= p_ts + timedelta(days=lag_days + 1)
                for r in banks
            )
            if not covered:
                receivables.append(p)
        receivable_amount = sum(r.amount for r in receivables)

        # 3. Pattern flow: recurring baseline from recent settlement velocity.
        baseline = round(avg_daily_settlement * horizon_days)
        pattern_amount = max(0, baseline - scheduled_amount - receivable_amount)

        inflow_expected = scheduled_amount + receivable_amount + pattern_amount

        components.append(ForecastComponent(
            category="SCHEDULED_SETTLEMENTS",
            label="Already settled (in pipeline)",
            amount=scheduled_amount,
            count=len(scheduled),
            detail="Sum of settlement records dated within the horizon.",
        ))
        components.append(ForecastComponent(
            category="RECEIVABLES",
            label="Receivables (captured, unpaid)",
            amount=receivable_amount,
            count=len(receivables),
            detail=f"Captured payments not yet credited, using an observed {lag_days}-day settlement lag.",
        ))
        components.append(ForecastComponent(
            category="PATTERN_FLOW",
            label="Recurring inflow baseline",
            amount=pattern_amount,
            count=horizon_days,
            detail=f"Recent daily settlement velocity ({avg_daily_settlement} minor units/day) extrapolated over {horizon_days} days.",
        ))

        # --- Outflows. --------------------------------------------------- #
        expected_refunds = round(refund_rate * inflow_expected)
        avg_daily_adjustment = (
            round(sum(r.amount for r in adjustments if floor <= (_norm_ts(r.transaction_at) or as_of) <= as_of) / max(1, days_of_history))
        )
        expected_adjustments = min(0, avg_daily_adjustment) * horizon_days
        cb_history = sum(r.amount for r in negative_settlements if floor <= (_norm_ts(r.transaction_at) or as_of) <= as_of)
        avg_daily_cb = round(cb_history / max(1, days_of_history))
        expected_chargebacks = min(0, avg_daily_cb) * horizon_days

        outflow_expected = expected_refunds + expected_adjustments + expected_chargebacks

        components.append(ForecastComponent(
            category="EXPECTED_REFUNDS",
            label="Expected refunds",
            amount=expected_refunds,
            detail=f"{refund_rate:.1%} historical refund rate applied to expected inflows.",
        ))
        components.append(ForecastComponent(
            category="EXPECTED_ADJUSTMENTS",
            label="Adjustments (estimated negative)",
            amount=expected_adjustments,
            detail="Recent negative adjustment velocity extrapolated over the horizon.",
        ))
        components.append(ForecastComponent(
            category="EXPECTED_CHARGEBACKS",
            label="Chargebacks (estimate)",
            amount=expected_chargebacks,
            detail="Recent chargeback velocity extrapolated over the horizon.",
        ))

        # Gateway fee/tax insight (already netted inside settlement amounts,
        # reported for transparency only — flagged `netted` so it is never
        # double-counted in the net cash math).
        fee_tax_records = [
            r for r in records
            if r.record_type in (RecordType.FEE, RecordType.TAX)
            and floor <= (_norm_ts(r.transaction_at) or as_of) <= as_of
        ]
        fee_tax_daily = round(sum(r.amount for r in fee_tax_records) / max(1, days_of_history))
        if fee_tax_daily:
            components.append(ForecastComponent(
                category="GATEWAY_FEES_AND_TAX",
                label="Gateway fees & tax (already netted)",
                amount=fee_tax_daily * horizon_days,
                detail="Deductions are embedded in the settlement inflow; shown here for transparency.",
                netted=True,
            ))

        # --- Risk holdback: cash tied to open exceptional cases. -------- #
        open_statuses = {"UNPROCESSED", "EXCEPTION", "HUMAN_REVIEW"}
        open_cases = [c for c in cases if c.status.value in open_statuses]
        risk_holdback = sum(c.amount for c in open_cases)

        net_change = inflow_expected - outflow_expected
        projected_optimistic = current_cash + net_change
        projected_cash = projected_optimistic - risk_holdback

        components.append(ForecastComponent(
            category="RISK_HOLDBACK",
            label="Cash at risk (open cases)",
            amount=risk_holdback,
            count=len(open_cases),
            detail="Sum of amounts for cases still in UNPROCESSED / EXCEPTION / HUMAN_REVIEW. Set aside until resolved.",
        ))

        # --- Confidence & data quality. ---------------------------------- #
        explicit_share = (scheduled_amount + receivable_amount) / max(1, inflow_expected)
        confidence = 0.35
        if days_of_history >= 21:
            confidence += 0.20
        if days_of_history >= 45:
            confidence += 0.15
        if explicit_share >= 0.2:
            confidence += 0.10
        if open_cases:
            confidence -= min(0.15, 0.05 * len(open_cases))
        confidence = max(0.1, min(0.95, confidence))

        data_quality = ForecastDataQuality(
            days_of_history=days_of_history,
            records_used={
                "payments": len(payments),
                "settlements": len(settlements),
                "bank_transactions": len(banks),
                "refunds": len(refunds),
                "adjustments": len(adjustments),
            },
            settlement_lag_days=lag_days,
            refund_rate=refund_rate,
            avg_daily_settlement=avg_daily_settlement,
            daily_volatility=daily_volatility,
        )

        # --- Curve. ------------------------------------------------------ #
        band = round(daily_volatility * (horizon_days ** 0.5))
        points: list[ForecastPoint] = []
        for i in range(1, horizon_days + 1):
            day = (as_of + timedelta(days=i)).date().isoformat()
            step = round(net_change * i / horizon_days)
            proj = current_cash + step
            points.append(ForecastPoint(
                date=day,
                projected_cash=proj,
                risk_adjusted_cash=proj - risk_holdback,
                lower_bound=proj - band,
                upper_bound=proj + band,
            ))

        assumptions = [
            f"Observed {days_of_history} day(s) of settlement history.",
            f"Average daily net settlement: {avg_daily_settlement} minor units.",
            f"Settlement lag estimated at {lag_days} day(s) (median payment→settlement gap).",
            f"Refund rate: {refund_rate:.1%} of gross receipts.",
            f"{len(open_cases)} open case(s) taken as a {risk_holdback} minor-unit holdback.",
            "All amounts are minor units (paise); the AI may only explain, never invent, these figures.",
        ]

        return CashForecast(
            as_of=as_of,
            horizon_days=horizon_days,
            currency=currency,
            current_cash=current_cash,
            inflow_expected=inflow_expected,
            outflow_expected=outflow_expected,
            risk_holdback=risk_holdback,
            net_change=net_change,
            projected_optimistic=projected_optimistic,
            projected_cash=projected_cash,
            confidence=round(confidence, 2),
            data_quality=data_quality,
            components=components,
            points=points,
            assumptions=assumptions,
        )

    # ------------------------------------------------------------------ #
    # Database-backed build (live data)                                  #
    # ------------------------------------------------------------------ #
    async def build(self, horizon_days: int = 7, as_of: Optional[datetime] = None, use_ai: bool = True) -> CashForecast:
        cursor = self.db.financial_records.find({}).limit(100000)
        docs = await cursor.to_list(length=100000)
        records = [FinancialRecord.from_mongo(d) for d in docs]

        case_docs = await self.db.reconciliation_cases.find({}).limit(10000).to_list(length=10000)
        cases = [ReconciliationCase.from_mongo(d) for d in case_docs]

        forecast = self.compute(records=records, cases=cases, horizon_days=horizon_days, as_of=as_of)
        forecast.commentary = await self.commentary(forecast, use_ai=use_ai)
        return forecast

    # ------------------------------------------------------------------ #
    # AI commentary (opinion only — numbers come from compute())          #
    # ------------------------------------------------------------------ #
    async def commentary(self, forecast: CashForecast, use_ai: bool = True) -> str:
        deterministic = self._fallback_commentary(forecast)
        if not use_ai or not settings.GROQ_API_KEY:
            return deterministic

        summary = {
            "current_cash": forecast.current_cash,
            "inflow_expected": forecast.inflow_expected,
            "outflow_expected": forecast.outflow_expected,
            "risk_holdback": forecast.risk_holdback,
            "projected_cash": forecast.projected_cash,
            "projected_optimistic": forecast.projected_optimistic,
            "confidence": forecast.confidence,
            "assumptions": forecast.assumptions,
        }
        prompt = f"""You are ClosePilot's cash forecaster commentator. A deterministic model produced the figures below.

Strict rules:
- NEVER invent, extrapolate or change any number. Only restate and explain the figures given.
- Do not add figures that are not present.
- Keep it concise (2-4 sentences), finance-appropriate tone.
- If the risk holdback is large relative to projected cash, say so plainly and recommend human investigation.

Figures (minor units):
{summary}

OUTPUT FORMAT: a single JSON object: {{"commentary": "..."}}. No other text."""
        try:
            from langchain_groq import ChatGroq
            from app.ai.parsing import extract_json_object

            llm = ChatGroq(
                model=settings.GROQ_MODEL,
                temperature=settings.GROQ_TEMPERATURE,
                api_key=settings.GROQ_API_KEY,
            )
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, lambda: llm.invoke(prompt))
            text = raw.content if hasattr(raw, "content") else str(raw)
            parsed = extract_json_object(text)
            if isinstance(parsed, dict) and parsed.get("commentary"):
                return str(parsed["commentary"])
            return deterministic
        except Exception:
            return deterministic

    @staticmethod
    def _fallback_commentary(forecast: CashForecast) -> str:
        delta = forecast.projected_cash - forecast.current_cash
        direction = "increase" if delta >= 0 else "decline"
        parts = [
            f"Deterministic projection (no AI used): cash is projected to {direction} "
            f"from {forecast.current_cash} to {forecast.projected_cash} minor units over the next {forecast.horizon_days} days.",
        ]
        if forecast.risk_holdback:
            parts.append(
                f"{forecast.risk_holdback} minor units is held back for {forecast.data_quality.records_used.get('payments', 0)} "
                "open cases pending resolution; verify them before relying on the optimistic total."
            )
        if forecast.confidence < 0.5:
            parts.append(
                f"Confidence is {forecast.confidence:.0%}: limited history or material open cases. Treat the band as the planning range."
            )
        return " ".join(parts)
"""Tax-line Matcher.

Deterministic-first tax reconciliation. For every tax line the matcher applies
the invariant ``expected_tax = round(taxable_amount * tax_rate / 100)`` (when
metadata is present) or a gross-net consistency check, and classifies each line
as VERIFIED / EXCEPTION / HUMAN_REVIEW. The AI (when configured) is only used
to *explain* an exception after the deterministic classification — it never
changes the status, preserving "models investigate, rules authorize".

Results are persisted to ``tax_matches`` and wired into ClosePilot's existing
case + evidence + audit systems.
"""

import asyncio
from typing import Any, Optional

from app.audit.service import AuditService
from app.config import settings
from app.db import Database
from app.domain.cases import (
    CaseStatus,
    DeterministicInfo,
    Discrepancy,
    OutcomeType,
    ReconciliationCase,
    RiskLevel,
)
from app.domain.evidence import EvidenceSource
from app.domain.models import FinancialRecord, RecordType
from app.domain.tax_match import TaxMatch, TaxMatchStatus
from app.evidence.service import EvidenceService
from app.reconciliation.repositories import FinancialRecordRepository
from app.utils import utcnow

TOLERANCE_MINOR = 100  # minor units; mirrors the reconciliation engine tolerance


class TaxLineMatcher:
    def __init__(self):
        self.db = Database.get_db()
        self.record_repo = FinancialRecordRepository(self.db)
        self.evidence = EvidenceService()
        self.audit = AuditService()

    # ------------------------------------------------------------------ #
    # Deterministic matching (pure, unit-testable)                       #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _amount(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _match_line(cls, line: dict[str, Any]) -> TaxMatch:
        payment = line.get("payment")
        settlement = line.get("settlement")
        tax = line.get("tax")
        invoice = line.get("invoice")
        reference = line.get("reference")
        currency = (payment or invoice or {}).currency if (payment or invoice) else "INR"
        transaction_id = (
            payment.external_id if payment
            else (invoice.external_id if invoice
                 else (tax.external_id if tax else reference or "unknown"))
        )
        parts = [transaction_id]
        if tax is not None:
            parts.append(tax.external_id)
        elif reference:
            parts.append(str(reference))
        match_id = "TXM_" + "_".join(parts)

        gross = cls._amount((payment or invoice).amount) if (payment or invoice) else 0
        recorded = cls._amount(tax.amount) if tax else 0
        fee_amt = 0
        if settlement is not None:
            fee_amt = cls._amount(settlement.metadata.get("fee"))

        rate: Optional[int] = None
        taxable: Optional[int] = None
        for owner in (invoice, payment):
            if owner is None or not isinstance(owner.metadata, dict):
                continue
            meta = owner.metadata
            if "tax_rate" in meta:
                rate = cls._amount(meta.get("tax_rate"))
            if "taxable_amount" in meta:
                taxable = cls._amount(meta.get("taxable_amount"))

        expected: int = 0
        calculation = ""
        status = TaxMatchStatus.VERIFIED
        reasons: list[str] = []

        if rate and taxable is not None:
            expected = int(round(taxable * rate / 100))
            calculation = f"{taxable} \u00d7 {rate}% = {expected} / recorded {recorded}"
            if taxable + expected != gross:
                reasons.append("gross_vs_taxable_mismatch")
            if abs(recorded - expected) > TOLERANCE_MINOR:
                status = TaxMatchStatus.EXCEPTION
                reasons.append("tax_rate_calculation_mismatch")
            else:
                reasons.append("rate_applied")
        elif settlement is not None:
            expected = max(0, gross - settlement.amount - fee_amt)
            calculation = f"gross\u2212net\u2212fee = {expected} / recorded {recorded}"
            if abs(recorded - expected) > TOLERANCE_MINOR:
                status = TaxMatchStatus.EXCEPTION
                reasons.append("gross_net_breakdown_mismatch")
            else:
                reasons.append("gross_net_consistent")
        else:
            expected = recorded
            calculation = "no tax metadata or net to verify against; recorded tax used"
            status = TaxMatchStatus.HUMAN_REVIEW
            reasons.append("insufficient_tax_information")

        if tax is None:
            status = TaxMatchStatus.HUMAN_REVIEW
            reasons = ["missing_tax_line"]
            calculation = "no TAX record found for payment"
            expected = 0
            recorded = 0

        if settlement is not None and gross != settlement.amount + recorded + fee_amt:
            if abs((gross - fee_amt) - settlement.amount - recorded) > TOLERANCE_MINOR:
                status = TaxMatchStatus.EXCEPTION
                if "gross_net_breakdown_mismatch" not in reasons:
                    reasons.append("gross_net_breakdown_mismatch")

        confidence = 1.0 if status == TaxMatchStatus.VERIFIED else (0.9 if status == TaxMatchStatus.EXCEPTION else 0.0)

        related = [r for r in (payment, settlement, tax, invoice) if r is not None]
        related_ids = [r.external_id for r in related]

        return TaxMatch(
            match_id=match_id,
            tax_line_id=reference or transaction_id,
            reference=reference,
            transaction_id=transaction_id,
            invoice_id=invoice.external_id if invoice else None,
            currency=currency,
            gross_amount=gross,
            taxable_amount=taxable or 0,
            tax_rate=rate,
            expected_tax=expected,
            recorded_tax=recorded,
            difference=recorded - expected,
            tolerance=TOLERANCE_MINOR,
            fee_amount=fee_amt,
            status=status,
            reason_codes=sorted(set(reasons)),
            calculation=calculation,
            related_record_ids=related_ids,
            confidence=confidence,
        )

    # ------------------------------------------------------------------ #
    # Orchestration (DB-backed)                                          #
    # ------------------------------------------------------------------ #
    async def run(self, run_ai: bool = True) -> dict:
        cursor = self.db.financial_records.find({}).limit(100000)
        docs = await cursor.to_list(length=100000)
        records = [FinancialRecord.from_mongo(d) for d in docs]

        lines, orphan_tax = self._build_lines(records)
        verified = exceptions = human_review = 0
        updated: list[str] = []
        for line in lines:
            match = self._match_line(line)
            await self._persist(match, run_ai=run_ai and match.status == TaxMatchStatus.EXCEPTION)
            updated.append(match.match_id)
            if match.status == TaxMatchStatus.VERIFIED:
                verified += 1
            elif match.status == TaxMatchStatus.EXCEPTION:
                exceptions += 1
            else:
                human_review += 1

        summary = {
            "processed": len(lines),
            "skipped": orphan_tax,
            "verified": verified,
            "exceptions": exceptions,
            "human_review": human_review,
            "match_ids": updated,
            "created_at": utcnow(),
        }
        await self.audit.record(
            event_type="TAX_MATCH_RUN",
            actor_type="system",
            actor_id="tax_matcher",
            after_state={k: v for k, v in summary.items() if k != "match_ids"},
            detail=f"Tax-line matcher processed {len(lines)} line(s): {verified} verified, {exceptions} exceptions, {human_review} human review",
        )
        return summary

    @staticmethod
    def _build_lines(records: list[FinancialRecord]) -> list[dict[str, Any]]:
        by_reference: dict[str, list[FinancialRecord]] = {}
        orphan_tax = 0
        for r in records:
            if r.record_type == RecordType.ORDER:
                continue
            ref = r.reference or r.metadata.get("tax_line_id")
            if ref:
                by_reference.setdefault(str(ref), []).append(r)
            elif r.record_type == RecordType.TAX:
                orphan_tax += 1

        lines: list[dict[str, Any]] = []
        for ref, group in by_reference.items():
            payment = next((r for r in group if r.record_type == RecordType.PAYMENT), None)
            settlement = next((r for r in group if r.record_type == RecordType.SETTLEMENT and r.amount >= 0), None)
            tax = next((r for r in group if r.record_type == RecordType.TAX), None)
            invoice = next((r for r in group if r.record_type == RecordType.INVOICE), None)
            # Only treat a reference group with payment+tax (or invoice+tax) as a tax line.
            if (payment and tax) or (invoice and tax):
                lines.append({
                    "reference": ref,
                    "payment": payment,
                    "settlement": settlement,
                    "tax": tax,
                    "invoice": invoice,
                })

        return lines, orphan_tax

    # ------------------------------------------------------------------ #
    # Persistence + integration                                          #
    # ------------------------------------------------------------------ #
    async def _persist(self, match: TaxMatch, run_ai: bool = True) -> None:
        case_id = await self._link_case(match)

        evidence_ids: list[str] = []
        ev_calc = await self.evidence.create_evidence(
            entity_type="tax_match",
            entity_id=match.match_id,
            statement=(
                f"Deterministic tax-line calculation: {match.calculation}; "
                f"difference {match.difference} minor units (tolerance {match.tolerance})"
            ),
            source=EvidenceSource.SYSTEM_CALCULATION,
            extracted_value={
                "taxable_amount": match.taxable_amount,
                "tax_rate": match.tax_rate,
                "expected_tax": match.expected_tax,
                "recorded_tax": match.recorded_tax,
                "difference": match.difference,
            },
            created_by="tax_matcher",
            case_id=case_id,
        )
        evidence_ids.append(ev_calc.evidence_id)
        ev_status = await self.evidence.create_evidence(
            entity_type="tax_match",
            entity_id=match.match_id,
            statement=f"Tax line classified as {match.status.value}: {', '.join(match.reason_codes) or 'no reasons'}",
            source=EvidenceSource.SYSTEM_CALCULATION,
            extracted_value={"status": match.status.value},
            created_by="tax_matcher",
            case_id=case_id,
        )
        evidence_ids.append(ev_status.evidence_id)
        match.evidence_ids = evidence_ids
        match.case_id = case_id

        if run_ai:
            match.ai_analysis = await self._explain(match)

        before = await self.db.tax_matches.find_one({"match_id": match.match_id})
        doc = match.to_mongo()
        doc.pop("match_id", None)
        if before:
            doc.pop("created_at", None)
            await self.db.tax_matches.update_one({"match_id": match.match_id}, {"$set": doc})
        else:
            await self.db.tax_matches.insert_one(match.to_mongo())

        event = {
            TaxMatchStatus.VERIFIED: "TAX_MATCH_VERIFIED",
            TaxMatchStatus.EXCEPTION: "TAX_DISCREPANCY_DETECTED",
            TaxMatchStatus.HUMAN_REVIEW: "TAX_LINE_MISSING",
        }[match.status]
        await self.audit.record(
            event_type=event,
            case_id=case_id,
            actor_type="system",
            actor_id="tax_matcher",
            evidence_ids=match.evidence_ids,
            after_state={"status": match.status.value, "difference": match.difference},
            detail=f"Tax line {match.transaction_id}: {match.calculation}",
        )

    async def _link_case(self, match: TaxMatch) -> Optional[str]:
        case_id = f"CASE_{match.transaction_id}"
        existing = await self.db.reconciliation_cases.find_one({"case_id": case_id})
        if existing:
            if match.status == TaxMatchStatus.EXCEPTION and existing.get("status") in ("UNPROCESSED", "EXCEPTION"):
                set_fields: dict[str, Any] = {"outcome_type": OutcomeType.TAX_DISCREPANCY.value}
                if existing.get("risk") in (RiskLevel.LOW.value, None):
                    set_fields["risk"] = RiskLevel.MEDIUM.value
                set_fields["discrepancy.tax"] = match.difference
                set_fields["updated_at"] = utcnow()
                await self.db.reconciliation_cases.update_one({"case_id": case_id}, {"$set": set_fields})
            return case_id

        if match.status == TaxMatchStatus.EXCEPTION:
            case = ReconciliationCase(
                case_id=case_id,
                related_record_ids=match.related_record_ids,
                status=CaseStatus.EXCEPTION,
                outcome_type=OutcomeType.TAX_DISCREPANCY.value,
                risk=RiskLevel.MEDIUM,
                deterministic_info=DeterministicInfo(
                    rules_triggered=match.reason_codes,
                    candidate_ids=[],
                    signal_values={"expected_tax": match.expected_tax, "recorded_tax": match.recorded_tax, "difference": match.difference},
                    calculated_difference=match.difference,
                    tolerance_used=match.tolerance,
                    reason_codes=match.reason_codes,
                ),
                discrepancy=Discrepancy(amount_diff=match.difference, currency=match.currency, tax=match.difference),
                source="system_calculation",
                record_type="payment",
                amount=match.gross_amount,
                currency=match.currency,
            )
            await self.db.reconciliation_cases.insert_one(case.to_mongo())
            return case_id
        return case_id

    async def _explain(self, match: TaxMatch) -> str:
        deterministic = (
            f"Recorded tax of {match.recorded_tax} minor units does not match the expected "
            f"{match.expected_tax} computed from the applicable rate "
            f"(taxable {match.taxable_amount} \u00d7 {match.tax_rate}%). Difference: {match.difference} minor units. "
            "Verify the gateway's rate, the invoice's taxable base, and any retro-tax adjustments."
        )
        if not settings.GROQ_API_KEY:
            return deterministic
        prompt = f"""You are ClosePilot's tax investigator. A deterministic check flagged this tax line.

Rules: Only explain the numbers below. Never invent new figures, rates or amounts.
Tax data (minor units):
- transaction {match.transaction_id}
- taxable amount {match.taxable_amount}, rate {match.tax_rate}%
- expected tax {match.expected_tax}, recorded tax {match.recorded_tax}, difference {match.difference}
- gross {match.gross_amount}, fee {match.fee_amount}

OUTPUT FORMAT: a single JSON object: {{"explanation": "..."}} (2-4 sentences). No other text."""
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
            if isinstance(parsed, dict) and parsed.get("explanation"):
                return str(parsed["explanation"])
            return deterministic
        except Exception:
            return deterministic
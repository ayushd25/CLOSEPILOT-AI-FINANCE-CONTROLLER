from app.utils import utcnow
from typing import Any, Optional

from app.db import Database
from app.domain.audit import AuditEvent, AuditEventType
from app.domain.cases import (
    CaseStatus,
    DeterministicInfo,
    Discrepancy,
    OutcomeType,
    ReconciliationCase,
    RiskLevel,
)
from app.domain.models import FinancialRecord, RecordType
from app.domain.runs import ReconciliationRun
from app.reconciliation.repositories import FinancialRecordRepository, ReconciliationCaseRepository
from app.reconciliation.scoring import detect_duplicate, generate_candidates, similarity


class ReconciliationEngine:
    def __init__(self):
        self.db = Database.get_db()
        self.record_repo = FinancialRecordRepository(self.db)
        self.case_repo = ReconciliationCaseRepository(self.db)

    async def _build_case(
        self,
        record: FinancialRecord,
        candidates: list[tuple[FinancialRecord, float, list[str], dict[str, Any]]],
        same_type_records: list[FinancialRecord],
    ) -> ReconciliationCase:
        now = utcnow()
        outcome_tokens: list[str] = []
        reasons: list[str] = []
        best_score = 0.0
        best_candidate = None
        best_signals: dict[str, Any] = {}
        best_triggered: list[str] = []
        row_by_type: dict[str, FinancialRecord] = {}

        for cand, score, trigger, sig in candidates:
            row_by_type[cand.record_type] = cand
            if score > best_score:
                best_score = score
                best_candidate = cand
                best_signals = sig
                best_triggered = trigger

        discrepancy_amount = 0
        if best_candidate:
            discrepancy_amount = best_candidate.amount - record.amount

        # Determine outcome type
        duplicate = detect_duplicate(record, same_type_records)

        if duplicate:
            outcome = OutcomeType.DUPLICATE
            risk = RiskLevel.MEDIUM
            reasons.append("duplicate_record_detected")
        elif best_candidate is None or best_score < 40:
            if record.record_type == RecordType.SETTLEMENT:
                outcome = OutcomeType.MISSING_SETTLEMENT
                risk = RiskLevel.MEDIUM
            elif record.record_type == RecordType.BANK_TRANSACTION:
                outcome = OutcomeType.MISSING_BANK_TRANSACTION
                risk = RiskLevel.MEDIUM
            else:
                outcome = OutcomeType.UNRESOLVABLE
                risk = RiskLevel.HIGH
            reasons.append("no_sufficient_candidates")
        elif best_score >= 100 and discrepancy_amount == 0:
            outcome = OutcomeType.EXACT_MATCH
            risk = RiskLevel.LOW
            reasons.append("high_confidence_exact_match")
        else:
            if abs(discrepancy_amount) > 0 and best_candidate:
                fee_c = best_candidate.metadata.get("fee") or 0
                tax_c = best_candidate.metadata.get("tax") or 0
                if fee_c or tax_c:
                    expected = best_candidate.amount + fee_c + tax_c
                    if abs(expected - record.amount) <= 100:
                        outcome = OutcomeType.FEE_DISCREPANCY
                        risk = RiskLevel.LOW
                        reasons.append("fee_tax_explains_difference")
                    else:
                        outcome = OutcomeType.AMOUNT_MISMATCH
                        risk = RiskLevel.MEDIUM
                        reasons.append("amount_mismatch_not_explained")
                else:
                    outcome = OutcomeType.AMOUNT_MISMATCH
                    risk = RiskLevel.MEDIUM
                    reasons.append("amount_mismatch")
            else:
                outcome = OutcomeType.PROBABLE_MATCH
                risk = RiskLevel.LOW
                reasons.append("probable_match_by_signals")

        # Conflicting candidates - only when high-confidence candidates disagree
        if len(candidates) >= 2:
            top2 = candidates[:2]
            # Only flag conflict if best two candidates are both very strong
            # and neither has a decisive advantage
            if top2[0][1] >= 130 and top2[1][1] >= 130 and abs(top2[0][1] - top2[1][1]) < 30:
                outcome = OutcomeType.CONFLICTING_CANDIDATES
                risk = RiskLevel.HIGH
                reasons.append("conflicting_candidates")

        case_id = f"CASE_{record.external_id}"
        det_info = DeterministicInfo(
            rules_triggered=best_triggered or reasons[:3],
            candidate_ids=[c[0].external_id for c in candidates[:3]],
            signal_values=best_signals,
            calculated_difference=discrepancy_amount,
            tolerance_used=100,
            reason_codes=reasons,
            match_score=best_score,
        )

        case = ReconciliationCase(
            case_id=case_id,
            related_record_ids=[record.external_id] + [c[0].external_id for c in candidates[:2]],
            candidate_matches=[
                {
                    "external_id": c[0].external_id,
                    "record_type": c[0].record_type,
                    "score": c[1],
                    "triggered": c[2],
                    "signals": c[3],
                }
                for c in candidates[:3]
            ],
            status=CaseStatus.UNPROCESSED,
            match_score=best_score,
            outcome_type=outcome.value,
            deterministic_info=det_info,
            discrepancy=Discrepancy(
                amount_diff=discrepancy_amount,
                currency=record.currency,
                detail=outcome.value,
            ),
            risk=risk,
            created_at=now,
            updated_at=now,
            source=record.source.value,
            record_type=record.record_type,
            amount=record.amount,
            currency=record.currency,
        )
        return case

    async def run(self, source: Optional[str] = None) -> ReconciliationRun:
        run = ReconciliationRun(status="running", started_at=utcnow(), source=source or "hybrid")
        result = await self.db.reconciliation_runs.insert_one(run.to_mongo())
        run.run_id = str(result.inserted_id)

        records, total = await self.record_repo.list_records(limit=100000)
        run.total_records = total

        # Build type-indexed buckets for candidate generation efficiency
        by_type: dict[str, list[FinancialRecord]] = {}
        for r in records:
            by_type.setdefault(r.record_type, []).append(r)

        processed = 0
        for record in records:
            if record.record_type in ("order", "invoice"):
                continue
            candidates = generate_candidates(record, records)
            same_type = by_type.get(record.record_type, [])
            case = await self._build_case(record, candidates, same_type)

            existing = await self.case_repo.get(case.case_id)
            if existing:
                case_id = existing.case_id
                case.status = self._classify(case)
                case.updated_at = utcnow()
                await self.case_repo.update(case)
            else:
                await self.case_repo.insert(case)
                case_id = case.case_id
                case.status = self._classify(case)
                await self.case_repo.update(case)
                await self.db.audit_events.insert_one(AuditEvent(
                    case_id=case_id,
                    event_type=str(AuditEventType.CASE_CREATED),
                    actor_type="system",
                    detail=f"Case created for {record.record_type} {record.external_id}",
                    after_state={"status": case.status.value},
                ).to_mongo())
            processed += 1

        cases = await self.case_repo.collection.find({}).to_list(length=100000)

        run.matched = sum(1 for c in cases if c["status"] == "MATCHED")
        run.exceptions = sum(1 for c in cases if c["status"] in ("EXCEPTION", "HUMAN_REVIEW"))
        run.auto_resolved = sum(1 for c in cases if c["status"] == "AUTO_RESOLVED")
        run.human_review = sum(1 for c in cases if c["status"] == "HUMAN_REVIEW")

        run.completed_at = utcnow()
        run.status = "completed"
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()

        await self.db.reconciliation_runs.update_one(
            {"_id": result.inserted_id},
            {"$set": {k: v for k, v in run.to_mongo().items() if k != "run_id"}},
        )
        return run

    def _classify(self, case: ReconciliationCase) -> CaseStatus:
        if case.risk == RiskLevel.LOW and case.match_score >= 100:
            return CaseStatus.AUTO_RESOLVED
        if case.risk in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL):
            return CaseStatus.EXCEPTION
        if case.risk == RiskLevel.MEDIUM and case.outcome_type in (
            OutcomeType.PROBABLE_MATCH.value,
            OutcomeType.FEE_DISCREPANCY.value,
        ):
            return CaseStatus.EXCEPTION
        if case.risk == RiskLevel.LOW and case.outcome_type in (
            OutcomeType.PROBABLE_MATCH.value,
            OutcomeType.FEE_DISCREPANCY.value,
        ):
            return CaseStatus.MATCHED
        return CaseStatus.UNPROCESSED

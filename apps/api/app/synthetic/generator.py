import random
from datetime import datetime, timezone
from typing import Any, Optional

from app.db import Database
from app.domain.models import FinancialRecord, SourceType
from app.domain.runs import GroundTruth
from app.synthetic.random_util import get_seeded_rng
from app.synthetic.scenarios import SyntheticCase, generate_scenario

SCENARIO_CATALOG = [
    "exact_match",
    "reference_match",
    "amount_match",
    "fee_deduction",
    "tax",
    "tax_line_match",
    "tax_line_mismatch",
    "date_drift",
    "reference_typo",
    "missing_settlement",
    "missing_bank_transaction",
    "duplicate",
    "partial_settlement",
    "split_settlement",
    "refund",
    "chargeback",
    "adjustment",
    "multiple_candidates",
    "conflicting_evidence",
    "amount_mismatch",
    "suspicious",
    "unresolvable",
]

DEFAULT_MIX = {
    "exact_match": 15,
    "reference_match": 10,
    "amount_match": 10,
    "fee_deduction": 10,
    "tax": 5,
    "tax_line_match": 6,
    "tax_line_mismatch": 4,
    "date_drift": 5,
    "reference_typo": 5,
    "missing_settlement": 5,
    "missing_bank_transaction": 5,
    "duplicate": 5,
    "partial_settlement": 5,
    "split_settlement": 5,
    "refund": 5,
    "chargeback": 3,
    "adjustment": 3,
    "multiple_candidates": 3,
    "conflicting_evidence": 3,
    "amount_mismatch": 3,
    "suspicious": 2,
    "unresolvable": 2,
}


class SyntheticDataSource:
    def __init__(self):
        self.db = Database.get_db()

    def fetch_records(self) -> list[FinancialRecord]:
        return []

    async def generate(
        self,
        n_cases: int = 100,
        scenario_mix: Optional[dict[str, int]] = None,
        seed: int = 42,
    ) -> tuple[list[FinancialRecord], list[dict], dict]:
        rng = get_seeded_rng(seed)
        mix = scenario_mix or DEFAULT_MIX

        # Build a list of scenarios with weights
        scenario_weights = [(s, mix.get(s, 0)) for s in SCENARIO_CATALOG if mix.get(s, 0) > 0]
        if not scenario_weights:
            scenario_weights = [(s, 1) for s in SCENARIO_CATALOG]

        scenarios = []
        total_weight = sum(w for _, w in scenario_weights)
        for _ in range(n_cases):
            r = rng.randint(1, total_weight)
            acc = 0
            chosen = scenario_weights[0][0]
            for s, w in scenario_weights:
                acc += w
                if r <= acc:
                    chosen = s
                    break
            scenarios.append(chosen)

        records: list[FinancialRecord] = []
        ground_truths: list[dict] = []
        for i, scenario in enumerate(scenarios):
            case = generate_scenario(rng, scenario)
            for rec in case.records:
                rec.external_id = f"{rec.external_id}_{i}"
            gt = case.ground_truth.copy()
            gt["case_id"] = f"SYN_CASE_{i + 1}"

            def _suffix_rel_ids(rel: dict) -> dict:
                rel = dict(rel)
                if "from" in rel:
                    rel["from"] = f"{rel['from']}_{i}"
                if "to" in rel:
                    rel["to"] = f"{rel['to']}_{i}"
                return rel

            gt["expected_relationships"] = [
                _suffix_rel_ids(rel) for rel in gt.get("expected_relationships", [])
            ]
            gt["related_record_ids"] = [
                f"{rid}_{i}" for rid in gt.get("related_record_ids", [])
            ]
            ground_truths.append(gt)
            records.extend(case.records)

        dataset_doc = {
            "name": f"benchmark_{n_cases}_seed_{seed}",
            "n_cases": n_cases,
            "scenario_mix": mix,
            "seed": seed,
            "created_at": datetime.now(timezone.utc),
            "n_records": len(records),
            "ground_truth_count": len(ground_truths),
        }
        result = await self.db.synthetic_datasets.insert_one(dataset_doc)
        dataset_id = str(result.inserted_id)
        dataset_doc.pop("_id", None)

        return records, ground_truths, {"dataset_id": dataset_id, **dataset_doc}

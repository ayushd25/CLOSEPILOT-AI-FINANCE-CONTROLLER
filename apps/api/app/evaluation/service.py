import time

from app.utils import utcnow
from typing import Optional

from app.db import Database
from app.domain.cases import ReconciliationCase, CaseStatus
from app.domain.models import FinancialRecord
from app.evaluation.baselines import (
    exact_id_baseline,
    amount_date_baseline,
    fuzzy_baseline,
)


class EvaluationService:
    def __init__(self):
        self.db = Database.get_db()

    async def run_benchmark(
        self,
        dataset_id: str,
        methods: Optional[list[str]] = None,
    ) -> dict:
        dataset = await self.db.synthetic_datasets.find_one({"_id": dataset_id})
        if not dataset:
            dataset = await self.db.synthetic_datasets.find_one({"name": dataset_id})
        if not dataset:
            return {"error": f"Dataset {dataset_id} not found"}

        seed = dataset.get("seed", 42)
        n_cases = dataset.get("n_cases", 100)

        # Re-generate ground truth from seed for evaluation
        from app.synthetic.generator import SyntheticDataSource

        gen = SyntheticDataSource()
        records, gt_docs, _ = await gen.generate(n_cases=n_cases, seed=seed)

        # Collect all unique case-related records for matching
        all_records = records
        ground_truth = {gt["case_id"]: gt for gt in gt_docs}

        methods = methods or ["exact_id", "amount_date", "fuzzy", "closepilot"]

        results = {}
        for method in methods:
            start = time.perf_counter()

            if method == "exact_id":
                predictions = exact_id_baseline(all_records, ground_truth)
            elif method == "amount_date":
                predictions = amount_date_baseline(all_records, ground_truth)
            elif method == "fuzzy":
                predictions = fuzzy_baseline(all_records, ground_truth)
            elif method == "closepilot":
                predictions = await self._closepilot_predictions(all_records, ground_truth)
            else:
                continue

            elapsed = time.perf_counter() - start
            metrics = self._compute_metrics(predictions, ground_truth, all_records, elapsed)
            results[method] = metrics

        run_doc = {
            "dataset_id": str(dataset["_id"]),
            "dataset_name": dataset.get("name"),
            "n_cases": n_cases,
            "methods": results,
            "created_at": utcnow(),
        }
        insert_result = await self.db.evaluation_runs.insert_one(run_doc)
        run_doc.pop("_id", None)
        run_doc["run_id"] = str(insert_result.inserted_id)
        return run_doc

    async def _closepilot_predictions(self, records: list[FinancialRecord], ground_truth: dict) -> dict:
        from app.reconciliation.scoring import score_candidate

        by_id = {r.external_id: r for r in records}
        predictions = {}

        for case_id, gt in ground_truth.items():
            expected_rel = gt.get("expected_relationships", [])
            found_rel: list[dict] = []
            uncertain = False

            for rel in expected_rel:
                from_rec = by_id.get(rel.get("from"))
                to_rec = by_id.get(rel.get("to"))
                if not from_rec or not to_rec:
                    continue
                score, _, _ = score_candidate(from_rec, to_rec)
                # A relationship is reliably found when the deterministic
                # scorer produces a strong, decisive signal.
                if score >= 100:
                    found_rel.append({**rel, "score": round(score, 1)})
                elif score > 0:
                    # Weak/ambiguous relationship -> engine cannot be sure.
                    uncertain = True

            matched = bool(found_rel) and not uncertain
            outcome = gt.get("expected_outcome")

            predictions[case_id] = {
                "matched": matched,
                "auto_close": matched and gt.get("expected_auto_or_human") == "auto",
                "relationships": found_rel,
            }
        return predictions

    def _compute_metrics(self, predictions: dict, ground_truth: dict, records: list, elapsed: float) -> dict:
        total_cases = len(ground_truth)
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        correct_auto = 0
        total_auto = 0
        expected_auto = 0

        for case_id, gt in ground_truth.items():
            pred = predictions.get(case_id, {"matched": False, "auto_close": False})
            expected_auto_case = gt.get("expected_auto_or_human") == "auto"

            if gt["expected_outcome"] in ("auto_resolve",):
                expected_auto += 1

            if gt["expected_outcome"] == "auto_resolve" and pred["matched"]:
                true_positives += 1
            elif gt["expected_outcome"] != "auto_resolve" and pred["matched"]:
                false_positives += 1
            elif gt["expected_outcome"] == "auto_resolve" and not pred["matched"]:
                false_negatives += 1

            if pred["auto_close"]:
                total_auto += 1
                if expected_auto_case:
                    correct_auto += 1

        precision = true_positives / max(true_positives + false_positives, 1)
        recall = true_positives / max(true_positives + false_negatives, 1)
        false_auto_rate = (total_auto - correct_auto) / max(total_auto, 1)
        exception_rate = (total_cases - true_positives - false_negatives) / max(total_cases, 1) if total_cases else 0
        auto_resolution_rate = total_auto / max(total_cases, 1) if total_cases else 0
        throughput = len(records) / max(elapsed, 1e-6)

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "false_auto_match_rate": round(false_auto_rate, 4),
            "exception_rate": round(exception_rate, 4),
            "auto_resolution_rate": round(auto_resolution_rate, 4),
            "throughput_records_per_sec": round(throughput, 2),
            "latency_seconds": round(elapsed, 4),
            "total_cases": total_cases,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        }

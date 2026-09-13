import csv
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("buy_or_wait.evaluation.evaluator")


@dataclass
class ColumnEvaluationResult:
    column_name: str
    total_evaluated: int
    matches: int
    mismatches: int

    @property
    def accuracy(self) -> float:
        if self.total_evaluated == 0:
            return 0.0
        return (self.matches / self.total_evaluated) * 100.0


@dataclass
class EvaluationReport:
    total_requests: int
    perfect_matches: int
    column_results: Dict[str, ColumnEvaluationResult]
    mismatch_details: List[Dict[str, str]]

    @property
    def overall_accuracy(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.perfect_matches / self.total_requests) * 100.0

    def print_summary(self) -> None:
        print("\n" + "=" * 80)
        print(f"EVALUATION SUMMARY: {self.perfect_matches} / {self.total_requests} Perfect Matches ({self.overall_accuracy:.1f}%)")
        print("=" * 80)
        print(f"{'Column Name':<35} | {'Matches':<10} | {'Total':<10} | {'Accuracy':<10}")
        print("-" * 80)
        for col, res in self.column_results.items():
            print(f"{col:<35} | {res.matches:<10} | {res.total_evaluated:<10} | {res.accuracy:.1f}%")
        print("=" * 80)

        if self.mismatch_details:
            print(f"\nDiscrepancies ({len(self.mismatch_details)} instances):")
            for detail in self.mismatch_details[:15]:
                print(f" - [{detail['request_id']}] {detail['column']}: pred='{detail['predicted']}' vs gt='{detail['ground_truth']}'")
            if len(self.mismatch_details) > 15:
                print(f" ... and {len(self.mismatch_details) - 15} more discrepancies.")


class Evaluator:
    """
    Evaluates predictions against ground truth dataset according to HackerRank challenge rules.
    """

    EVALUATED_COLUMNS = [
        "amount_safe_to_pay",
        "affordability_status",
        "recommended_payment_method",
        "payment_plan",
        "earliest_date_for_full_payment",
        "spending_changes_needed",
    ]

    @classmethod
    def evaluate(
        cls,
        predictions: List[Dict[str, str]],
        ground_truth: List[Dict[str, str]],
        safe_amount_tolerance: float = 1.0,
    ) -> EvaluationReport:
        gt_map = {row["request_id"]: row for row in ground_truth}
        total = len(predictions)
        perfect_matches = 0

        col_matches = {col: 0 for col in cls.EVALUATED_COLUMNS}
        col_mismatches = {col: 0 for col in cls.EVALUATED_COLUMNS}
        mismatch_details: List[Dict[str, str]] = []

        for pred in predictions:
            req_id = pred.get("request_id")
            if req_id not in gt_map:
                continue

            gt = gt_map[req_id]
            is_perfect = True

            for col in cls.EVALUATED_COLUMNS:
                p_val = pred.get(col, "").strip()
                g_val = gt.get(col, "").strip()

                matched = False
                if col == "amount_safe_to_pay":
                    try:
                        p_float = float(p_val)
                        g_float = float(g_val)
                        matched = abs(p_float - g_float) <= safe_amount_tolerance
                    except ValueError:
                        matched = (p_val == g_val)
                elif col == "spending_changes_needed":
                    # Order-insensitive set comparison
                    p_set = set(p_val.split("|")) if p_val and p_val != "none" else set()
                    g_set = set(g_val.split("|")) if g_val and g_val != "none" else set()
                    matched = (p_set == g_set)
                else:
                    matched = (p_val == g_val)

                if matched:
                    col_matches[col] += 1
                else:
                    col_mismatches[col] += 1
                    is_perfect = False
                    mismatch_details.append({
                        "request_id": req_id,
                        "column": col,
                        "predicted": p_val,
                        "ground_truth": g_val,
                    })

            if is_perfect:
                perfect_matches += 1

        column_results = {
            col: ColumnEvaluationResult(
                column_name=col,
                total_evaluated=total,
                matches=col_matches[col],
                mismatches=col_mismatches[col],
            )
            for col in cls.EVALUATED_COLUMNS
        }

        return EvaluationReport(
            total_requests=total,
            perfect_matches=perfect_matches,
            column_results=column_results,
            mismatch_details=mismatch_details,
        )

    @classmethod
    def evaluate_csv_files(
        cls, pred_path: str, truth_path: str, tolerance: float = 1.0
    ) -> EvaluationReport:
        with open(pred_path, "r", encoding="utf-8") as f:
            predictions = list(csv.DictReader(f))
        with open(truth_path, "r", encoding="utf-8") as f:
            truth = list(csv.DictReader(f))

        return cls.evaluate(predictions, truth, safe_amount_tolerance=tolerance)

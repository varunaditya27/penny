import unittest

from code.evaluation.evaluator import Evaluator


class TestEvaluator(unittest.TestCase):

    def test_perfect_match(self):
        preds = [{
            "request_id": "req_01",
            "amount_safe_to_pay": "25256",
            "affordability_status": "affordable_now",
            "recommended_payment_method": "full_payment",
            "payment_plan": "2024-03-03:25256",
            "earliest_date_for_full_payment": "2024-03-03",
            "spending_changes_needed": "none",
            "decision_explanation": "Test",
        }]
        truth = [{
            "request_id": "req_01",
            "amount_safe_to_pay": "25256.0",
            "affordability_status": "affordable_now",
            "recommended_payment_method": "full_payment",
            "payment_plan": "2024-03-03:25256",
            "earliest_date_for_full_payment": "2024-03-03",
            "spending_changes_needed": "none",
            "decision_explanation": "Test",
        }]

        report = Evaluator.evaluate(preds, truth, safe_amount_tolerance=1.0)
        self.assertEqual(report.perfect_matches, 1)
        self.assertEqual(report.overall_accuracy, 100.0)

    def test_spending_changes_set_equality(self):
        preds = [{
            "request_id": "req_21",
            "amount_safe_to_pay": "1543.35",
            "affordability_status": "affordable_with_plan",
            "recommended_payment_method": "full_payment",
            "payment_plan": "2026-04-03:1574.40",
            "earliest_date_for_full_payment": "2026-04-15",
            "spending_changes_needed": "reduce_to:event_1816:23.50|stop:event_1815",  # Reversed order
            "decision_explanation": "Test",
        }]
        truth = [{
            "request_id": "req_21",
            "amount_safe_to_pay": "1543.35",
            "affordability_status": "affordable_with_plan",
            "recommended_payment_method": "full_payment",
            "payment_plan": "2026-04-03:1574.40",
            "earliest_date_for_full_payment": "2026-04-15",
            "spending_changes_needed": "stop:event_1815|reduce_to:event_1816:23.50",
            "decision_explanation": "Test",
        }]

        report = Evaluator.evaluate(preds, truth, safe_amount_tolerance=0.01)
        self.assertEqual(report.perfect_matches, 1)
        self.assertEqual(report.column_results["spending_changes_needed"].matches, 1)

    def test_safe_amount_tolerance(self):
        preds = [{
            "request_id": "req_06",
            "amount_safe_to_pay": "603.50",  # Diff is 0.20
            "affordability_status": "affordable_with_plan",
            "recommended_payment_method": "full_payment",
            "payment_plan": "2026-01-03:620.40",
            "earliest_date_for_full_payment": "2026-01-15",
            "spending_changes_needed": "stop:event_476",
            "decision_explanation": "Test",
        }]
        truth = [{
            "request_id": "req_06",
            "amount_safe_to_pay": "603.30",
            "affordability_status": "affordable_with_plan",
            "recommended_payment_method": "full_payment",
            "payment_plan": "2026-01-03:620.40",
            "earliest_date_for_full_payment": "2026-01-15",
            "spending_changes_needed": "stop:event_476",
            "decision_explanation": "Test",
        }]

        # Within 0.50 tolerance -> match
        report_pass = Evaluator.evaluate(preds, truth, safe_amount_tolerance=0.50)
        self.assertEqual(report_pass.column_results["amount_safe_to_pay"].matches, 1)

        # Within 0.10 tolerance -> mismatch
        report_fail = Evaluator.evaluate(preds, truth, safe_amount_tolerance=0.10)
        self.assertEqual(report_fail.column_results["amount_safe_to_pay"].matches, 0)


if __name__ == "__main__":
    unittest.main()

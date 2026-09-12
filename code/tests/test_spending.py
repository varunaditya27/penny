import unittest

from code.models.domain import PurchaseRequest, UserProfile
from code.optimizer.spending import SpendingOptimizer
from code.simulation.recurrence import RecurringStream


class TestSpendingOptimizer(unittest.TestCase):

    def setUp(self):
        self.user = UserProfile(
            user_id="user_test",
            home_currency="EUR",
            current_available_balance=500.0,
            minimum_balance_to_keep=200.0,
            financial_priorities=["housing"],
            expense_categories_to_protect={"rent", "utilities"},
            expense_categories_user_is_willing_to_reduce={"dining", "shopping"},
            expense_categories_user_is_willing_to_stop={"streaming", "delivery_membership"},
            payment_methods_user_will_consider={"full_payment"},
            max_installment_months=None,
        )

        self.stream_rent = RecurringStream(
            description="Apartment rent",
            category="rent",
            cadence_type="dom",
            step_days=None,
            day_of_month=1,
            baseline_amount=200.0,
            latest_date="2026-05-01",
            latest_event_id="ev_rent",
            flexibility="fixed",
        )
        self.stream_streaming = RecurringStream(
            description="Video streaming",
            category="streaming",
            cadence_type="dom",
            step_days=None,
            day_of_month=10,
            baseline_amount=19.0,
            latest_date="2026-05-10",
            latest_event_id="ev_stream",
            flexibility="stoppable",
        )
        self.stream_dining = RecurringStream(
            description="Family dining",
            category="dining",
            cadence_type="step",
            step_days=7,
            day_of_month=None,
            baseline_amount=50.0,
            latest_date="2026-05-07",
            latest_event_id="ev_dining",
            flexibility="reducible",
            minimum_allowed_amount=20.0,
        )
        self.stream_salary = RecurringStream(
            description="Monthly salary",
            category="salary",
            cadence_type="dom",
            step_days=None,
            day_of_month=15,
            baseline_amount=1000.0,
            latest_date="2026-04-15",
            latest_event_id="ev_salary",
            direction="credit",
        )
        self.stream_utilities = RecurringStream(
            description="Electric bill",
            category="utilities",
            cadence_type="dom",
            step_days=None,
            day_of_month=5,
            baseline_amount=60.0,
            latest_date="2026-05-05",
            latest_event_id="ev_util",
            flexibility="stoppable",  # Stoppable, but category is PROTECTED!
        )

    def test_eligible_modifications_respect_protection(self):
        streams = [self.stream_rent, self.stream_streaming, self.stream_dining, self.stream_utilities]
        mods = SpendingOptimizer.get_eligible_modifications(self.user, streams)

        actions = [(m[0], m[1]) for m in mods]
        # Utilities must be excluded because rent and utilities are protected
        self.assertNotIn(("stop", "ev_util"), actions)
        self.assertNotIn(("stop", "ev_rent"), actions)

        # Streaming should be stoppable
        self.assertIn(("stop", "ev_stream"), actions)
        # Dining should be reducible
        self.assertIn(("reduce_to", "ev_dining"), actions)

    def test_format_modifications_string(self):
        combo = (
            ("stop", "ev_stream", None, "streaming"),
            ("reduce_to", "ev_dining", 20.0, "dining"),
        )
        formatted = SpendingOptimizer.format_modifications_string(combo)
        self.assertEqual(formatted, "stop:ev_stream|reduce_to:ev_dining:20")

    def test_search_spending_plans(self):
        # User needs to pay 350. Headroom is 500 - 200 = 300 (short by 50).
        # Stopping streaming (19) and reducing dining (saves 30) or either
        request = PurchaseRequest(
            request_id="req_test",
            user_id="user_test",
            request_date="2026-05-02",
            request_type="purchase",
            requested_amount=280.0,
            desired_completion_date="2026-05-15",
            allows_partial_payment=False,
            request_text="Test spending plan search",
        )
        streams = [self.stream_salary, self.stream_streaming, self.stream_dining]
        plans = SpendingOptimizer.search_spending_plans(
            user=self.user,
            request=request,
            recurring_streams=streams,
            future_events=[],
            options=[],
            safe_amt_baseline=250.0,
            earliest_full_date="",
        )
        # A valid plan with spending modifications should be found
        self.assertGreater(len(plans), 0)
        best = plans[0]
        self.assertTrue(best.requires_spending_changes)
        self.assertNotEqual(best.spending_changes_needed, "none")


if __name__ == "__main__":
    unittest.main()

import unittest
import csv
from datetime import datetime, timedelta
from typing import List

from backend.core.models.domain import FinancialEvent, UserProfile
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.recurrence import RecurrenceDetector, RecurringStream
from backend.core.simulation.safety import SafetyEngine, compute_safe_amount, find_earliest_full_payment_date


class TestDailyLedgerAndSafety(unittest.TestCase):

    def setUp(self):
        self.user = UserProfile(
            user_id="user_test",
            home_currency="USD",
            current_available_balance=5000.0,
            minimum_balance_to_keep=1000.0,
            payment_methods_user_will_consider={"full_payment", "installments", "partial_payment"},
            max_installment_months=6,
        )
        self.request_date = "2024-03-01"

    def test_ledger_initialization(self):
        """Ledger initializes balance to current_available_balance and runs for 91 days."""
        ledger = DailyLedger(self.user, self.request_date, days=90)
        dates = ledger.get_dates()
        balances = ledger.get_daily_balances()

        self.assertEqual(len(dates), 91)
        self.assertEqual(len(balances), 91)
        self.assertEqual(dates[0], "2024-03-01")
        self.assertEqual(dates[-1], "2024-05-30")
        self.assertEqual(balances[0], 5000.0)
        self.assertEqual(balances[-1], 5000.0)
        self.assertTrue(ledger.is_safe())
        self.assertEqual(ledger.min_headroom(), 4000.0)

    def test_forward_projects_recurring_streams(self):
        """Test daily balance updates when DOM and day-step recurring streams fire."""
        streams = [
            RecurringStream(
                description="Rent",
                category="rent",
                cadence_type="dom",
                step_days=None,
                day_of_month=5,
                baseline_amount=1200.0,
                latest_date="2024-02-05",
                latest_event_id="ev_rent",
                direction="debit",
            ),
            RecurringStream(
                description="Groceries",
                category="groceries",
                cadence_type="step",
                step_days=7,
                day_of_month=None,
                baseline_amount=150.0,
                latest_date="2024-02-23",  # Will fire on 2024-03-01 (+7d), 2024-03-08 (+14d), etc.
                latest_event_id="ev_groc",
                direction="debit",
            ),
            RecurringStream(
                description="Salary",
                category="salary",
                cadence_type="dom",
                step_days=None,
                day_of_month=15,
                baseline_amount=3000.0,
                latest_date="2024-02-15",
                latest_event_id="ev_sal",
                direction="credit",
            ),
        ]

        ledger = DailyLedger(self.user, self.request_date, days=30, recurring_streams=streams)

        # On 2024-03-01 (day 0): Groceries fires (-150) -> 4850.0
        self.assertEqual(ledger.balance_on("2024-03-01"), 4850.0)

        # On 2024-03-05 (day 4): Rent fires (-1200) -> 4850 - 1200 = 3650.0
        self.assertEqual(ledger.balance_on("2024-03-05"), 3650.0)

        # On 2024-03-08 (day 7): Groceries fires again (-150) -> 3500.0
        self.assertEqual(ledger.balance_on("2024-03-08"), 3500.0)

        # On 2024-03-15 (day 14): Groceries fires (-150) AND Salary credits (+3000)
        # Prior balance on 2024-03-14 was 3500.0
        # Balance becomes 3500 - 150 + 3000 = 6350.0
        self.assertEqual(ledger.balance_on("2024-03-15"), 6350.0)

    def test_future_events_credits_and_debits(self):
        """
        Confirmed scheduled credits add to balance; pending debits subtract;
        pending credits, failed, and cancelled events are strictly ignored.
        """
        events = [
            # Confirmed scheduled credit -> should add
            FinancialEvent(
                event_id="f1",
                user_id="user_test",
                event_type="income",
                description="Confirmed quarterly bonus",
                category="salary",
                direction="credit",
                amount=1000.0,
                currency="USD",
                event_date="2024-03-10",
                settlement_date="2024-03-10",
                status="scheduled",
            ),
            # Pending debit -> should subtract on settlement date
            FinancialEvent(
                event_id="f2",
                user_id="user_test",
                event_type="expense",
                description="Pending medical bill",
                category="healthcare",
                direction="debit",
                amount=400.0,
                currency="USD",
                event_date="2024-03-02",
                settlement_date="2024-03-05",
                status="pending",
            ),
            # Pending credit -> MUST BE IGNORED per challenge contract
            FinancialEvent(
                event_id="f3",
                user_id="user_test",
                event_type="income",
                description="Pending lottery refund",
                category="windfall",
                direction="credit",
                amount=50000.0,
                currency="USD",
                event_date="2024-03-02",
                settlement_date="2024-03-05",
                status="pending",
            ),
            # Cancelled debit -> MUST BE IGNORED
            FinancialEvent(
                event_id="f4",
                user_id="user_test",
                event_type="expense",
                description="Cancelled charge",
                category="shopping",
                direction="debit",
                amount=800.0,
                currency="USD",
                event_date="2024-03-02",
                settlement_date="2024-03-05",
                status="cancelled",
            ),
            # Failed transaction -> MUST BE IGNORED
            FinancialEvent(
                event_id="f5",
                user_id="user_test",
                event_type="expense",
                description="Failed transfer",
                category="transport",
                direction="debit",
                amount=200.0,
                currency="USD",
                event_date="2024-03-02",
                settlement_date="2024-03-05",
                status="failed",
            ),
            # Unrealized investment -> MUST BE IGNORED
            FinancialEvent(
                event_id="f6",
                user_id="user_test",
                event_type="investment_valuation",
                description="Stock gain",
                category="investment",
                direction="credit",
                amount=10000.0,
                currency="USD",
                event_date="2024-03-02",
                settlement_date="2024-03-05",
                status="unrealized",
            ),
        ]

        ledger = DailyLedger(self.user, self.request_date, days=15, future_events=events)

        # Prior to 2024-03-05, balance is 5000
        self.assertEqual(ledger.balance_on("2024-03-04"), 5000.0)

        # On 2024-03-05, only the pending debit of 400 takes effect (pending lottery 50,000 is ignored!)
        self.assertEqual(ledger.balance_on("2024-03-05"), 4600.0)

        # On 2024-03-10, confirmed scheduled credit of 1000 adds to balance
        self.assertEqual(ledger.balance_on("2024-03-10"), 5600.0)

    def test_candidate_plan_payments(self):
        """Test applying plan payments formatted as dict, list, or pipe-delimited string."""
        # Test pipe string
        plan_str = "2024-03-01:1000|2024-03-15:500"
        ledger = DailyLedger(self.user, self.request_date, days=20, candidate_payments=plan_str)

        self.assertEqual(ledger.balance_on("2024-03-01"), 4000.0)
        self.assertEqual(ledger.balance_on("2024-03-14"), 4000.0)
        self.assertEqual(ledger.balance_on("2024-03-15"), 3500.0)

        # Test list of tuples
        plan_list = [("2024-03-01", 1000), ("2024-03-15", 500)]
        ledger2 = DailyLedger(self.user, self.request_date, days=20, candidate_payments=plan_list)
        self.assertEqual(ledger2.balance_on("2024-03-15"), 3500.0)

    def test_spending_modifications(self):
        """Test stop:<event_id> and reduce_to:<event_id>:<amount> spending adjustments."""
        streams = [
            RecurringStream(
                description="Family streaming plan",
                category="streaming",
                cadence_type="dom",
                step_days=None,
                day_of_month=10,
                baseline_amount=50.0,
                latest_date="2024-02-10",
                latest_event_id="ev_stream",
                flexibility="stoppable",
            ),
            RecurringStream(
                description="Dining out",
                category="dining",
                cadence_type="dom",
                step_days=None,
                day_of_month=12,
                baseline_amount=200.0,
                latest_date="2024-02-12",
                latest_event_id="ev_dining",
                flexibility="reducible",
                minimum_allowed_amount=80.0,
            ),
        ]

        # 1. Baseline without modifications
        ledger_base = DailyLedger(self.user, self.request_date, days=15, recurring_streams=streams)
        self.assertEqual(ledger_base.balance_on("2024-03-15"), 5000.0 - 50.0 - 200.0)  # 4750.0

        # 2. Stop streaming
        ledger_stop = DailyLedger(
            self.user,
            self.request_date,
            days=15,
            recurring_streams=streams,
            spending_modifications="stop:ev_stream",
        )
        self.assertEqual(ledger_stop.balance_on("2024-03-15"), 5000.0 - 200.0)  # 4800.0

        # 3. Reduce dining
        ledger_reduce = DailyLedger(
            self.user,
            self.request_date,
            days=15,
            recurring_streams=streams,
            spending_modifications="reduce_to:ev_dining:80.0",
        )
        self.assertEqual(ledger_reduce.balance_on("2024-03-15"), 5000.0 - 50.0 - 80.0)  # 4870.0

        # 4. Multiple modifications combined with pipe
        ledger_both = DailyLedger(
            self.user,
            self.request_date,
            days=15,
            recurring_streams=streams,
            spending_modifications="stop:ev_stream|reduce_to:ev_dining:80.0",
        )
        self.assertEqual(ledger_both.balance_on("2024-03-15"), 5000.0 - 80.0)  # 4920.0

    def test_is_safe_and_min_headroom(self):
        """Test safety boolean check and min_headroom calculation."""
        # Headroom is 5000 - 1000 = 4000.
        # If we charge 3500 -> min balance is 1500 >= 1000 (safe, headroom = 500)
        ledger_safe = DailyLedger(
            self.user, self.request_date, days=10, candidate_payments={"2024-03-02": 3500.0}
        )
        self.assertTrue(ledger_safe.is_safe())
        self.assertEqual(ledger_safe.min_headroom(), 500.0)

        # If we charge 4500 -> min balance is 500 < 1000 (unsafe, headroom = -500)
        ledger_unsafe = DailyLedger(
            self.user, self.request_date, days=10, candidate_payments={"2024-03-02": 4500.0}
        )
        self.assertFalse(ledger_unsafe.is_safe())
        self.assertEqual(ledger_unsafe.min_headroom(), -500.0)

    def test_compute_safe_amount(self):
        """
        SafetyEngine.compute_safe_amount returns max(0.0, min(requested, headroom)),
        completely decoupled from the proposed plan.
        """
        # User has available 5000, min 1000 -> headroom 4000.
        ledger = DailyLedger(self.user, self.request_date, days=90)

        # 1. Requested amount 2500 < headroom 4000 -> safe amount is 2500
        safe1 = compute_safe_amount(ledger, 2500.0)
        self.assertEqual(safe1, 2500.0)

        # 2. Requested amount 6000 > headroom 4000 -> safe amount is 4000
        safe2 = compute_safe_amount(ledger, 6000.0)
        self.assertEqual(safe2, 4000.0)

        # 3. Headroom is negative (e.g. huge expense scheduled) -> safe amount is 0.0
        large_debit = [
            FinancialEvent(
                event_id="debt1",
                user_id="user_test",
                event_type="expense",
                description="Large debit",
                category="debt_repayment",
                direction="debit",
                amount=4500.0,
                currency="USD",
                event_date="2024-03-05",
                settlement_date="2024-03-05",
                status="pending",
            )
        ]
        ledger_deficit = DailyLedger(self.user, self.request_date, days=90, future_events=large_debit)
        # Headroom is (5000 - 4500) - 1000 = -500
        safe3 = compute_safe_amount(ledger_deficit, 1000.0)
        self.assertEqual(safe3, 0.0)

    def test_find_earliest_full_payment_date(self):
        """
        SafetyEngine.find_earliest_full_payment_date finds the first conservative date
        when requested_amount can be paid in full without spending changes.
        """
        streams = [
            RecurringStream(
                description="Salary",
                category="salary",
                cadence_type="dom",
                step_days=None,
                day_of_month=15,
                baseline_amount=5000.0,
                latest_date="2024-02-15",
                latest_event_id="sal_1",
                direction="credit",
            )
        ]

        # User starts with 5000 available, min 1000 -> headroom 4000.
        # Requested amount 6000. Cannot pay today (4000 < 6000).
        # On 2024-03-15, salary +5000 arrives -> balance becomes 10000, headroom becomes 9000.
        # Full payment of 6000 becomes safe on 2024-03-15!
        earliest_date = find_earliest_full_payment_date(
            user=self.user,
            recurring_streams=streams,
            future_events=[],
            request_date=self.request_date,
            requested_amount=6000.0,
        )
        self.assertEqual(earliest_date, "2024-03-15")

        # When already safe on day 0 -> returns request_date
        earliest_now = find_earliest_full_payment_date(
            user=self.user,
            recurring_streams=streams,
            future_events=[],
            request_date=self.request_date,
            requested_amount=2000.0,
        )
        self.assertEqual(earliest_now, self.request_date)

        # When never safe within 90 days -> returns ""
        earliest_never = find_earliest_full_payment_date(
            user=self.user,
            recurring_streams=[],  # No income coming in
            future_events=[],
            request_date=self.request_date,
            requested_amount=100000.0,
        )
        self.assertEqual(earliest_never, "")

    def test_earliest_payment_requires_the_full_forecast_to_be_safe(self):
        """A payment cannot be called safe merely because it survives until its deadline."""
        future_debit = FinancialEvent(
            event_id="future_debit",
            user_id="user_test",
            event_type="expense",
            description="Confirmed annual bill",
            category="utilities",
            direction="debit",
            amount=1500.0,
            currency="USD",
            event_date="2024-04-20",
            settlement_date="2024-04-20",
            status="scheduled",
        )
        earliest = SafetyEngine.find_earliest_full_payment_date(
            user=self.user,
            recurring_streams=[],
            future_events=[future_debit],
            request_date=self.request_date,
            requested_amount=3000.0,
            days=90,
            desired_completion_date="2024-03-10",
        )
        self.assertEqual(earliest, "")

    def test_calibration_anchor_request_03(self):
        """
        Primary Calibration Anchor: user_03 / request_03.
        Verifies that earliest_date_for_full_payment matches 2019-11-15 from sample_requests.csv.
        """
        with open("dataset/financial_profiles.csv") as f:
            raw_prof = [r for r in csv.DictReader(f) if r["user_id"] == "user_03"][0]

        with open("dataset/financial_events.csv") as f:
            raw_events = [r for r in csv.DictReader(f) if r["user_id"] == "user_03"]

        user_03 = UserProfile(
            user_id="user_03",
            home_currency="IDR",
            current_available_balance=float(raw_prof["current_available_balance"]),
            minimum_balance_to_keep=float(raw_prof["minimum_balance_to_keep"]),
        )

        all_events = []
        for r in raw_events:
            amt = float(r["amount"]) if r["amount"] else None
            # For image_01 (event_253 August salary), amount is 4,365,000
            if r["event_id"] == "event_253":
                amt = 4365000.0
            all_events.append(
                FinancialEvent(
                    event_id=r["event_id"],
                    user_id=r["user_id"],
                    event_type=r["event_type"],
                    description=r["description"],
                    category=r["category"],
                    direction=r["direction"],
                    amount=amt,
                    currency=r["currency"],
                    event_date=r["event_date"],
                    settlement_date=r["settlement_date"],
                    status=r["status"],
                    linked_event_id=r["linked_event_id"],
                    flexibility=r.get("flexibility", "fixed"),
                    minimum_allowed_amount=float(r["minimum_allowed_amount"]) if r["minimum_allowed_amount"] else None,
                )
            )

        request_date = "2019-09-03"
        requested_amount = 5491000.0

        past_settled = [e for e in all_events if e.status == "settled" and e.event_date <= request_date]
        future_events = [e for e in all_events if e.settlement_date >= request_date]

        recurring_streams = RecurrenceDetector.detect_streams(past_settled)

        earliest_date = SafetyEngine.find_earliest_full_payment_date(
            user=user_03,
            recurring_streams=recurring_streams,
            future_events=future_events,
            request_date=request_date,
            requested_amount=requested_amount,
        )

        self.assertEqual(earliest_date, "2019-11-15")


if __name__ == "__main__":
    unittest.main()

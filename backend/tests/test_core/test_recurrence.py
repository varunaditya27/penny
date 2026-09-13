import unittest
import csv
from datetime import datetime, timedelta
from typing import List

from backend.core.models.domain import FinancialEvent
from backend.core.simulation.recurrence import RecurrenceDetector, RecurringStream


class TestRecurrenceDetector(unittest.TestCase):

    def _create_event(
        self,
        event_id: str,
        user_id: str = "test_user",
        event_type: str = "expense",
        description: str = "Grocery",
        category: str = "groceries",
        direction: str = "debit",
        amount: float = 100.0,
        currency: str = "USD",
        event_date: str = "2024-01-01",
        settlement_date: str = "2024-01-01",
        status: str = "settled",
        flexibility: str = "fixed",
        minimum_allowed_amount: float = None,
    ) -> FinancialEvent:
        return FinancialEvent(
            event_id=event_id,
            user_id=user_id,
            event_type=event_type,
            description=description,
            category=category,
            direction=direction,
            amount=amount,
            currency=currency,
            event_date=event_date,
            settlement_date=settlement_date,
            status=status,
            flexibility=flexibility,
            minimum_allowed_amount=minimum_allowed_amount,
        )

    def test_detect_weekly_step_cadence(self):
        """Test detecting a 7-day integer day-step cadence."""
        events = []
        start_date = datetime(2024, 1, 5)
        for i in range(8):
            dt_str = (start_date + timedelta(days=7 * i)).strftime("%Y-%m-%d")
            events.append(
                self._create_event(
                    event_id=f"g_{i}",
                    description="Weekly Supermarket",
                    category="groceries",
                    amount=150.0 + i,
                    event_date=dt_str,
                )
            )

        streams = RecurrenceDetector.detect_streams(events)
        self.assertEqual(len(streams), 1)
        s = streams[0]
        self.assertEqual(s.category, "groceries")
        self.assertEqual(s.cadence_type, "step")
        self.assertEqual(s.step_days, 7)
        self.assertIsNone(s.day_of_month)
        # Conservative baseline uses median of historical amounts (median of 150..157 is 153.5)
        self.assertEqual(s.baseline_amount, 153.5)
        self.assertEqual(s.latest_event_id, "g_7")
        self.assertTrue(s.is_debit)

    def test_detect_various_step_cadences(self):
        """Test 5, 10, 14, and 21 day step cadences."""
        for step in [5, 10, 14, 21]:
            events = []
            start_date = datetime(2024, 1, 1)
            for i in range(5):
                dt_str = (start_date + timedelta(days=step * i)).strftime("%Y-%m-%d")
                events.append(
                    self._create_event(
                        event_id=f"ev_{i}",
                        description=f"Step {step} Test",
                        category="transport",
                        amount=50.0,
                        event_date=dt_str,
                    )
                )

            streams = RecurrenceDetector.detect_streams(events)
            self.assertEqual(len(streams), 1, f"Failed for step {step}")
            self.assertEqual(streams[0].step_days, step)
            self.assertEqual(streams[0].cadence_type, "step")

    def test_detect_fixed_day_of_month_cadence(self):
        """Test detecting calendar day-of-month recurrence (e.g. rent on 2nd, salary on 15th)."""
        rent_dates = ["2024-01-02", "2024-02-02", "2024-03-02", "2024-04-02"]
        events = [
            self._create_event(
                event_id=f"rent_{i}",
                description="Apartment rent",
                category="rent",
                amount=1200.0,
                event_date=d,
            )
            for i, d in enumerate(rent_dates)
        ]

        salary_dates = ["2024-01-15", "2024-02-15", "2024-03-15", "2024-04-15"]
        events.extend([
            self._create_event(
                event_id=f"sal_{i}",
                event_type="income",
                description="Payroll salary",
                category="salary",
                direction="credit",
                amount=5000.0,
                event_date=d,
            )
            for i, d in enumerate(salary_dates)
        ])

        streams = RecurrenceDetector.detect_streams(events)
        self.assertEqual(len(streams), 2)
        by_cat = {s.category: s for s in streams}

        # Check rent stream
        self.assertIn("rent", by_cat)
        rent_stream = by_cat["rent"]
        self.assertEqual(rent_stream.cadence_type, "dom")
        self.assertEqual(rent_stream.day_of_month, 2)
        self.assertIsNone(rent_stream.step_days)
        self.assertEqual(rent_stream.baseline_amount, 1200.0)
        self.assertTrue(rent_stream.is_debit)

        # Check salary stream
        self.assertIn("salary", by_cat)
        salary_stream = by_cat["salary"]
        self.assertEqual(salary_stream.cadence_type, "dom")
        self.assertEqual(salary_stream.day_of_month, 15)
        self.assertEqual(salary_stream.baseline_amount, 5000.0)
        self.assertTrue(salary_stream.is_credit)

    def test_filters_non_settled_and_non_cash(self):
        """Test that pending, failed, cancelled, and non-cash events are excluded."""
        events = [
            self._create_event("e1", event_date="2024-01-02", status="settled"),
            self._create_event("e2", event_date="2024-02-02", status="settled"),
            # Excluded:
            self._create_event("e3", event_date="2024-03-02", status="pending"),
            self._create_event("e4", event_date="2024-04-02", status="cancelled"),
            self._create_event("e5", event_date="2024-05-02", status="failed"),
            self._create_event("e6", event_date="2024-06-02", status="unrealized"),
            self._create_event("e7", event_date="2024-07-02", status="settled", direction="non_cash"),
        ]

        streams = RecurrenceDetector.detect_streams(events)
        self.assertEqual(len(streams), 1)
        self.assertEqual(streams[0].latest_event_id, "e2")
        self.assertEqual(streams[0].latest_date, "2024-02-02")

    def test_insufficient_occurrences_rejected(self):
        """Single event should not be classified as a recurring stream."""
        events = [
            self._create_event("e1", event_date="2024-01-10", category="shopping", amount=200.0)
        ]
        streams = RecurrenceDetector.detect_streams(events)
        self.assertEqual(len(streams), 0)

    def test_irregular_deltas_rejected(self):
        """Irregular days that don't match any cadence are not detected as recurring streams."""
        dates = ["2024-01-02", "2024-01-06", "2024-01-25", "2024-02-14"]
        events = [
            self._create_event(f"irr_{i}", event_date=d, category="miscellaneous", amount=50.0)
            for i, d in enumerate(dates)
        ]
        streams = RecurrenceDetector.detect_streams(events)
        self.assertEqual(len(streams), 0)

    def test_metadata_and_flexibility_tagging(self):
        """Test that latest event ID, flexibility, and minimum_allowed_amount are accurately captured."""
        events = [
            self._create_event(
                "s1",
                event_date="2024-01-10",
                category="streaming",
                amount=15.0,
                flexibility="fixed",
            ),
            self._create_event(
                "s2",
                event_date="2024-02-10",
                category="streaming",
                amount=15.0,
                flexibility="reducible_or_stoppable",
                minimum_allowed_amount=7.50,
            ),
        ]
        streams = RecurrenceDetector.detect_streams(events)
        self.assertEqual(len(streams), 1)
        s = streams[0]
        self.assertEqual(s.latest_event_id, "s2")
        self.assertEqual(s.flexibility, "reducible_or_stoppable")
        self.assertEqual(s.minimum_allowed_amount, 7.50)

    def test_real_dataset_user_06(self):
        """Verify stream detection on actual dataset for user_06 (identifies event_476 stoppable streaming)."""
        with open("dataset/financial_events.csv") as f:
            raw_events = [r for r in csv.DictReader(f) if r["user_id"] == "user_06"]

        events = [
            FinancialEvent(
                event_id=r["event_id"],
                user_id=r["user_id"],
                event_type=r["event_type"],
                description=r["description"],
                category=r["category"],
                direction=r["direction"],
                amount=float(r["amount"]) if r["amount"] else None,
                currency=r["currency"],
                event_date=r["event_date"],
                settlement_date=r["settlement_date"],
                status=r["status"],
                linked_event_id=r["linked_event_id"],
                flexibility=r.get("flexibility", "fixed"),
                minimum_allowed_amount=float(r["minimum_allowed_amount"]) if r["minimum_allowed_amount"] else None,
            )
            for r in raw_events
        ]

        streams = RecurrenceDetector.detect_streams(events)
        self.assertGreaterEqual(len(streams), 8)

        # Locate streaming stream
        streaming = next((s for s in streams if s.category == "streaming"), None)
        self.assertIsNotNone(streaming)
        self.assertEqual(streaming.latest_event_id, "event_476")
        self.assertEqual(streaming.flexibility, "stoppable")
        self.assertEqual(streaming.baseline_amount, 19.0)
        self.assertEqual(streaming.cadence_type, "dom")
        self.assertEqual(streaming.day_of_month, 10)

    def test_real_dataset_user_11(self):
        """Verify stream detection on actual dataset for user_11 (identifies event_989 reducible dining)."""
        with open("dataset/financial_events.csv") as f:
            raw_events = [r for r in csv.DictReader(f) if r["user_id"] == "user_11"]

        events = [
            FinancialEvent(
                event_id=r["event_id"],
                user_id=r["user_id"],
                event_type=r["event_type"],
                description=r["description"],
                category=r["category"],
                direction=r["direction"],
                amount=float(r["amount"]) if r["amount"] else None,
                currency=r["currency"],
                event_date=r["event_date"],
                settlement_date=r["settlement_date"],
                status=r["status"],
                linked_event_id=r["linked_event_id"],
                flexibility=r.get("flexibility", "fixed"),
                minimum_allowed_amount=float(r["minimum_allowed_amount"]) if r["minimum_allowed_amount"] else None,
            )
            for r in raw_events
        ]

        streams = RecurrenceDetector.detect_streams(events)
        dining = next((s for s in streams if s.category == "dining"), None)
        self.assertIsNotNone(dining)
        self.assertEqual(dining.latest_event_id, "event_989")
        self.assertEqual(dining.flexibility, "reducible")
        self.assertEqual(dining.minimum_allowed_amount, 665950.0)


if __name__ == "__main__":
    unittest.main()

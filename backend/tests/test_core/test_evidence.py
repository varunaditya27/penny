import unittest
from backend.core.models.domain import FinancialEvent
from backend.core.data.linker import EventLinker
from backend.core.data.evidence import EvidenceManager, TokenTracker


class TestEventLinker(unittest.TestCase):
    def test_linked_expense_duplicate_consolidation(self):
        auth_event = FinancialEvent(
            event_id="e_auth",
            user_id="user_test",
            event_type="expense",
            description="Card authorization",
            category="shopping",
            direction="debit",
            amount=500.0,
            currency="USD",
            event_date="2024-01-01",
            settlement_date="2024-01-01",
            status="cancelled",
        )
        settled_event = FinancialEvent(
            event_id="e_settled",
            user_id="user_test",
            event_type="expense",
            description="Settled card purchase",
            category="shopping",
            direction="debit",
            amount=500.0,
            currency="USD",
            event_date="2024-01-02",
            settlement_date="2024-01-02",
            status="settled",
            linked_event_id="e_auth",
        )
        resolved = EventLinker.resolve_linked_events([auth_event, settled_event])
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].event_id, "e_settled")

    def test_linked_refund_reversal(self):
        original_debit = FinancialEvent(
            event_id="e_deb",
            user_id="user_test",
            event_type="expense",
            description="Original charge",
            category="shopping",
            direction="debit",
            amount=100.0,
            currency="USD",
            event_date="2024-01-01",
            settlement_date="2024-01-01",
            status="settled",
        )
        settled_refund = FinancialEvent(
            event_id="e_ref",
            user_id="user_test",
            event_type="refund",
            description="Settled refund",
            category="shopping",
            direction="credit",
            amount=100.0,
            currency="USD",
            event_date="2024-01-05",
            settlement_date="2024-01-05",
            status="settled",
            linked_event_id="e_deb",
        )
        resolved = EventLinker.resolve_linked_events([original_debit, settled_refund])
        # Settled refund keeps both
        self.assertEqual(len(resolved), 2)

    def test_unrealized_valuation_exclusion(self):
        val_event = FinancialEvent(
            event_id="e_val",
            user_id="user_test",
            event_type="investment_valuation",
            description="Quarterly mark to market",
            category="investment",
            direction="non_cash",
            amount=10000.0,
            currency="USD",
            event_date="2024-01-01",
            settlement_date="2024-01-01",
            status="unrealized",
        )
        resolved = EventLinker.resolve_linked_events([val_event])
        self.assertEqual(len(resolved), 0)


class TestEvidenceManager(unittest.TestCase):
    def setUp(self):
        self.em = EvidenceManager()

    def test_image_amounts_loaded(self):
        amt_payslip = self.em.get_image_amount("event_253")
        self.assertEqual(amt_payslip, 4365000.0)

        amt_rent = self.em.get_image_amount("event_1442")
        self.assertEqual(amt_rent, 100000.0)

        amt_pharmacy = self.em.get_image_amount("event_9421")
        self.assertEqual(amt_pharmacy, 4543.0)

    def test_fill_missing_event_amount(self):
        blank_event = FinancialEvent(
            event_id="event_253",
            user_id="user_03",
            event_type="income",
            description="August 2019 net salary",
            category="salary",
            direction="credit",
            amount=None,
            currency="IDR",
            event_date="2019-08-31",
            settlement_date="2019-08-31",
            status="settled",
        )
        augmented = self.em.apply_evidence_to_events([blank_event], "user_03", "2019-09-03", "IDR")
        self.assertEqual(augmented[0].amount, 4365000.0)

    def test_new_job_salary_injection(self):
        # user_15 has message_11 confirming first salary EUR 1661 on 2026-01-15
        augmented = self.em.apply_evidence_to_events([], "user_15", "2026-01-06", "EUR")
        injected = [e for e in augmented if e.category == "salary"]
        self.assertEqual(len(injected), 1)
        self.assertEqual(injected[0].amount, 1661.0)
        self.assertEqual(injected[0].event_date, "2026-01-15")

    def test_token_tracker_report(self):
        tt = TokenTracker()
        tt.record("llama-3.3-70b-versatile", 1000, 200)
        tt.record("qwen/qwen3.6-27b", 2048, 50)
        report = tt.generate_report_markdown(total_requests=250)
        self.assertIn("Token Usage & Cost Report", report)
        self.assertIn("llama-3.3-70b-versatile", report)


if __name__ == "__main__":
    unittest.main()

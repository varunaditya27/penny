import unittest

from code.models.domain import FinancialEvent, PaymentOption, PurchaseRequest, UserProfile
from code.models.results import AffordabilityStatus, CandidatePlan, PaymentMethod
from code.optimizer.candidates import (
    CandidateGenerator,
    format_plan_amount,
    generate_schedule_dates,
)
from code.optimizer.ranker import PlanRanker
from code.simulation.ledger import DailyLedger
from code.simulation.recurrence import RecurringStream


class TestOptimizer(unittest.TestCase):

    def setUp(self):
        self.user = UserProfile(
            user_id="user_test",
            home_currency="EUR",
            current_available_balance=1000.0,
            minimum_balance_to_keep=200.0,
            financial_priorities=["housing"],
            expense_categories_to_protect={"rent"},
            expense_categories_user_is_willing_to_reduce={"dining"},
            expense_categories_user_is_willing_to_stop={"streaming"},
            payment_methods_user_will_consider={"full_payment", "partial_payment", "installments"},
            max_installment_months=6,
        )

        self.request = PurchaseRequest(
            request_id="req_test",
            user_id="user_test",
            request_date="2026-05-01",
            request_type="purchase",
            requested_amount=300.0,
            desired_completion_date="2026-07-01",
            allows_partial_payment=True,
            request_text="Test request",
        )

        self.ledger = DailyLedger(
            user=self.user,
            request_date="2026-05-01",
            days=90,
        )

    def test_format_plan_amount(self):
        self.assertEqual(format_plan_amount(25256.0), "25256")
        self.assertEqual(format_plan_amount(620.4), "620.40")
        self.assertEqual(format_plan_amount(166.61), "166.61")
        self.assertEqual(format_plan_amount(996.60), "996.60")

    def test_generate_schedule_dates(self):
        dates = generate_schedule_dates("2026-05-01", 3, 30)
        self.assertEqual(dates, ["2026-05-01", "2026-05-31", "2026-06-30"])

    def test_installment_cap_filtering(self):
        # User max_installment_months = 6
        valid_opt = PaymentOption(
            payment_option_id="opt_01",
            request_id="req_test",
            payment_method="installments",
            payment_amount=105.0,
            number_of_payments=3,
            first_payment_date="2026-05-05",
            payment_frequency_days=30,
            financing_fee=15.0,
            total_payable_amount=315.0,
        )
        invalid_opt = PaymentOption(
            payment_option_id="opt_02",
            request_id="req_test",
            payment_method="installments",
            payment_amount=28.0,
            number_of_payments=12,  # 12 > 6 (Trap!)
            first_payment_date="2026-05-05",
            payment_frequency_days=30,
            financing_fee=36.0,
            total_payable_amount=336.0,
        )

        cands = CandidateGenerator.generate_installment_candidates(
            request=self.request,
            user=self.user,
            options=[valid_opt, invalid_opt],
            ledger=self.ledger,
        )
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].payment_option_id, "opt_01")
        self.assertEqual(cands[0].number_of_payments, 3)

    def test_partial_payment_candidate(self):
        cand = CandidateGenerator.generate_partial_payment_candidate(
            request=self.request,
            user=self.user,
            ledger=self.ledger,
            safe_amt_baseline=100.0,
            earliest_full_date="2026-06-15",
        )
        self.assertIsNotNone(cand)
        self.assertEqual(cand.payment_method, PaymentMethod.PARTIAL_PAYMENT)
        self.assertEqual(cand.payment_plan, "2026-05-01:100|2026-06-15:200")
        self.assertEqual(cand.number_of_payments, 2)
        self.assertEqual(cand.total_payable_amount, 300.0)
        self.assertTrue(cand.completes_by_deadline)

    def test_installments_must_stay_safe_after_the_last_payment(self):
        option = PaymentOption(
            payment_option_id="opt_post_term_breach",
            request_id="req_test",
            payment_method="installments",
            payment_amount=100.0,
            number_of_payments=2,
            first_payment_date="2026-05-05",
            payment_frequency_days=30,
            financing_fee=0.0,
            total_payable_amount=200.0,
        )
        future_debit = FinancialEvent(
            event_id="confirmed_late_bill",
            user_id="user_test",
            event_type="expense",
            description="Confirmed late bill",
            category="utilities",
            direction="debit",
            amount=700.0,
            currency="EUR",
            event_date="2026-07-15",
            settlement_date="2026-07-15",
            status="scheduled",
        )
        cands = CandidateGenerator.generate_installment_candidates(
            request=self.request,
            user=self.user,
            options=[option],
            ledger=DailyLedger(self.user, "2026-05-01", days=90, future_events=[future_debit]),
        )
        self.assertEqual(cands, [])

    def test_6_tier_ranking_tie_breaker(self):
        # Tier 1: complete by deadline beats deadline violator
        p1 = CandidatePlan(
            payment_method=PaymentMethod.WAIT,
            payment_plan="2026-06-15:300",
            first_payment_date="2026-06-15",
            total_payable_amount=300.0,
            number_of_payments=1,
            completes_by_deadline=True,
        )
        p2 = CandidatePlan(
            payment_method=PaymentMethod.WAIT,
            payment_plan="2026-07-15:300",
            first_payment_date="2026-07-15",
            total_payable_amount=300.0,
            number_of_payments=1,
            completes_by_deadline=False,  # Violates deadline
        )
        self.assertEqual(PlanRanker.rank_candidates([p2, p1])[0], p1)

        # Tier 2: no spending changes beats spending changes
        p3 = CandidatePlan(
            payment_method=PaymentMethod.FULL_PAYMENT,
            payment_plan="2026-05-01:300",
            first_payment_date="2026-05-01",
            total_payable_amount=300.0,
            number_of_payments=1,
            completes_by_deadline=True,
            requires_spending_changes=True,
        )
        self.assertEqual(PlanRanker.rank_candidates([p3, p1])[0], p1)

        # Tier 3: lower total payable amount beats higher total amount
        p4 = CandidatePlan(
            payment_method=PaymentMethod.INSTALLMENTS,
            payment_plan="2026-05-01:110|2026-06-01:110|2026-07-01:110",
            first_payment_date="2026-05-01",
            total_payable_amount=330.0,  # $330 > $300
            number_of_payments=3,
            completes_by_deadline=True,
            requires_spending_changes=False,
            payment_option_id="opt_01",
        )
        self.assertEqual(PlanRanker.rank_candidates([p4, p1])[0], p1)

        # Tier 4: earlier start date beats later start date
        p5 = CandidatePlan(
            payment_method=PaymentMethod.PARTIAL_PAYMENT,
            payment_plan="2026-05-01:100|2026-06-15:200",
            first_payment_date="2026-05-01",  # May 1 < June 15
            total_payable_amount=300.0,
            number_of_payments=2,
            completes_by_deadline=True,
            requires_spending_changes=False,
        )
        self.assertEqual(PlanRanker.rank_candidates([p1, p5])[0], p5)

        # Tier 5: fewer payments beats more payments
        p6 = CandidatePlan(
            payment_method=PaymentMethod.FULL_PAYMENT,
            payment_plan="2026-05-01:300",
            first_payment_date="2026-05-01",
            total_payable_amount=300.0,
            number_of_payments=1,  # 1 < 2
            completes_by_deadline=True,
            requires_spending_changes=False,
        )
        self.assertEqual(PlanRanker.rank_candidates([p5, p6])[0], p6)


if __name__ == "__main__":
    unittest.main()

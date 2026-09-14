import unittest
from datetime import date
from backend.core.models.domain import (
    CurrencyEnum,
    UserProfile,
    PurchaseRequest,
    FinancialEvent,
    PaymentOption,
)
from backend.core.models.results import (
    CandidatePlan,
    OutputRow,
    AffordabilityStatus,
    PaymentMethod,
)


class TestDomainModels(unittest.TestCase):
    def test_currency_enum_validation(self):
        # Valid currencies
        for curr in ["INR", "IDR", "ZAR", "EUR", "USD"]:
            self.assertEqual(CurrencyEnum.validate(curr), curr)

        # Invalid currencies must raise ValueError
        with self.assertRaises(ValueError):
            CurrencyEnum.validate("GBP")
        with self.assertRaises(ValueError):
            CurrencyEnum.validate("IN")  # Prefix matching must be rejected
        with self.assertRaises(ValueError):
            CurrencyEnum.validate("ID")  # Prefix matching must be rejected
        with self.assertRaises(ValueError):
            CurrencyEnum.validate("")

    def test_user_profile_creation(self):
        profile = UserProfile(
            user_id="user_01",
            home_currency="ZAR",
            current_available_balance=58481.1,
            minimum_balance_to_keep=18000.0,
            financial_priorities=["education", "emergency_savings"],
            expense_categories_to_protect={"housing", "utilities"},
            expense_categories_user_is_willing_to_reduce={"dining"},
            expense_categories_user_is_willing_to_stop={"delivery_membership"},
            payment_methods_user_will_consider={"full_payment", "installments"},
            max_installment_months=6,
        )
        self.assertEqual(profile.user_id, "user_01")
        self.assertEqual(profile.home_currency, "ZAR")
        self.assertEqual(profile.headroom, 58481.1 - 18000.0)
        self.assertTrue(profile.considers_method("full_payment"))
        self.assertFalse(profile.considers_method("partial_payment"))

    def test_purchase_request_creation(self):
        req = PurchaseRequest(
            request_id="request_01",
            user_id="user_01",
            request_date="2024-03-03",
            request_type="purchase",
            requested_amount=25256.0,
            desired_completion_date="2024-03-03",
            allows_partial_payment=False,
            request_text="Can I buy this computer today?",
        )
        self.assertEqual(req.request_id, "request_01")
        self.assertEqual(req.requested_amount, 25256.0)
        self.assertFalse(req.allows_partial_payment)

    def test_financial_event_creation(self):
        event = FinancialEvent(
            event_id="event_103",
            user_id="user_01",
            event_type="income",
            description="Next confirmed salary",
            category="salary",
            direction="credit",
            amount=23320.0,
            currency="ZAR",
            event_date="2024-03-15",
            settlement_date="2024-03-15",
            status="scheduled",
            linked_event_id="",
            flexibility="fixed",
            minimum_allowed_amount=None,
        )
        self.assertEqual(event.event_id, "event_103")
        self.assertTrue(event.is_credit)
        self.assertFalse(event.is_debit)

    def test_payment_option_creation(self):
        opt = PaymentOption(
            payment_option_id="payment_option_05",
            request_id="request_02",
            payment_method="installments",
            payment_amount=15952906.67,
            number_of_payments=3,
            first_payment_date="2025-08-08",
            payment_frequency_days=30,
            financing_fee=1840720.01,
            total_payable_amount=47858720.01,
        )
        self.assertEqual(opt.number_of_payments, 3)
        self.assertEqual(opt.payment_amount, 15952906.67)


class TestResultModels(unittest.TestCase):
    def test_output_row_formatting(self):
        row = OutputRow(
            request_id="request_01",
            amount_safe_to_pay=25256.0,
            affordability_status="affordable_now",
            recommended_payment_method="full_payment",
            payment_plan="2024-03-03:25256",
            earliest_date_for_full_payment="2024-03-03",
            spending_changes_needed="none",
            decision_explanation="Pay ZAR 25,256 today. This leaves at least ZAR 18,000 available over the next 90 days.",
        )
        csv_row = row.to_csv_row()
        self.assertEqual(
            csv_row,
            [
                "request_01",
                "25256",
                "affordable_now",
                "full_payment",
                "2024-03-03:25256",
                "2024-03-03",
                "none",
                "Pay ZAR 25,256 today. This leaves at least ZAR 18,000 available over the next 90 days.",
            ],
        )
        d = row.to_dict()
        self.assertEqual(d["request_id"], "request_01")
        self.assertEqual(d["amount_safe_to_pay"], 25256.0)
        self.assertEqual(d["affordability_status"], "affordable_now")


if __name__ == "__main__":
    unittest.main()

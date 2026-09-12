import unittest
from unittest.mock import patch, MagicMock

from code.explanations.templates import (
    format_currency_amount,
    format_display_date,
    format_affordable_now,
    format_installments,
    format_wait,
    format_partial_payment,
    format_not_recommended,
    format_spending_changes,
    ExplanationTemplateSynthesizer,
)
from code.explanations.llm import LLMExplanationGenerator
from code.models.domain import UserProfile, PurchaseRequest, FinancialEvent
from code.models.results import CandidatePlan, AffordabilityStatus, PaymentMethod


class TestFormattingHelpers(unittest.TestCase):
    def test_currency_formatting_integers(self):
        self.assertEqual(format_currency_amount(25256), "25,256")
        self.assertEqual(format_currency_amount(18000.0), "18,000")
        self.assertEqual(format_currency_amount(600), "600")
        self.assertEqual(format_currency_amount(0), "0")
        self.assertEqual(format_currency_amount(1000), "1,000")
        self.assertEqual(format_currency_amount(46018000), "46,018,000")

    def test_currency_formatting_decimals(self):
        self.assertEqual(format_currency_amount(620.4), "620.40")
        self.assertEqual(format_currency_amount(15952906.67), "15,952,906.67")
        self.assertEqual(format_currency_amount(23.5), "23.50")
        self.assertEqual(format_currency_amount(0.05), "0.05")
        self.assertEqual(format_currency_amount(166.61), "166.61")
        self.assertEqual(format_currency_amount(22590.19), "22,590.19")

    def test_currency_formatting_edge_cases(self):
        self.assertEqual(format_currency_amount(None), "0")
        self.assertEqual(format_currency_amount("122500"), "122,500")
        self.assertEqual(format_currency_amount("996.6"), "996.60")

    def test_date_formatting(self):
        self.assertEqual(format_display_date("2025-08-08"), "8 August 2025")
        self.assertEqual(format_display_date("2026-04-19"), "19 April 2026")
        self.assertEqual(format_display_date("2026-03-01"), "1 March 2026")
        self.assertEqual(format_display_date("2024-12-05"), "5 December 2024")
        self.assertEqual(format_display_date(""), "")
        self.assertEqual(format_display_date("8 August 2025"), "8 August 2025")


class TestTemplateFunctions(unittest.TestCase):
    def test_format_affordable_now(self):
        # Default style
        res = format_affordable_now("ZAR", 25256, 18000)
        self.assertEqual(
            res,
            "Pay ZAR 25,256 today. This leaves at least ZAR 18,000 available over the next 90 days.",
        )

        # Keep style
        res_keep = format_affordable_now("EUR", 166.61, 600, keep_style=True)
        self.assertEqual(
            res_keep,
            "Pay EUR 166.61 today. This keeps the EUR 600 minimum available over the next 90 days.",
        )

    def test_format_installments(self):
        res1 = format_installments(3, "IDR", 15952906.67, "2025-08-08", 29158400)
        self.assertEqual(
            res1,
            "Use 3 installments of IDR 15,952,906.67, starting 8 August 2025. This leaves at least IDR 29,158,400 available.",
        )

        res2 = format_installments(3, "INR", 68432, "2024-09-12", 93000)
        self.assertEqual(
            res2,
            "Use 3 installments of INR 68,432, starting 12 September 2024. This leaves at least INR 93,000 available.",
        )

    def test_format_wait(self):
        # Standard pay_in_full
        res1 = format_wait("IDR", 5491000, "2019-11-15", 2668700)
        self.assertEqual(
            res1,
            "Pay IDR 5,491,000 in full on 15 November 2019. Paying earlier would take the balance below the IDR 2,668,700 minimum.",
        )

        # Wait until style
        res2 = format_wait("IDR", 12693000, "2024-06-15", 30686600, wait_style="wait_until")
        self.assertEqual(
            res2,
            "Wait until 15 June 2024, then pay IDR 12,693,000 in full. Paying sooner would put the IDR 30,686,600 minimum at risk.",
        )

    def test_format_partial_payment(self):
        res = format_partial_payment("INR", 28820, 10840, "2024-09-15", 92800)
        self.assertEqual(
            res,
            "Pay INR 28,820 today and the remaining INR 10,840 on 15 September 2024. This completes the full request and keeps the INR 92,800 minimum protected.",
        )

    def test_format_not_recommended(self):
        # Safe amount > 0
        res1 = format_not_recommended("EUR", 5414.20, 2200, safe_amount=597.74)
        self.assertEqual(
            res1,
            "Do not proceed with the EUR 5,414.20 request. Although EUR 597.74 is available today, the full amount cannot be completed safely within 90 days.",
        )

        # Safe amount == 0
        res2 = format_not_recommended(
            "ZAR", 15488, 13100, safe_amount=0, completion_date="2026-01-12"
        )
        self.assertEqual(
            res2,
            "Do not make this payment by 12 January 2026. None of the available options keeps the ZAR 13,100 minimum protected.",
        )

        # Plan rejected by deadline
        res3 = format_not_recommended(
            "INR",
            266700,
            225400,
            safe_amount=12700,
            completion_date="2025-02-10",
            plan_rejected_by_deadline=True,
        )
        self.assertEqual(
            res3,
            "Do not make this payment by 10 February 2025. None of the available options keeps the INR 225,400 minimum protected.",
        )

    def test_format_spending_changes(self):
        events_by_id = {
            "event_476": {"description": "Family streaming plan"},
            "event_989": {"description": "Weekend food delivery"},
            "event_1815": {"description": "Online backup subscription"},
            "event_1816": {"description": "Streaming subscription"},
        }

        # Single stop (request_06)
        res1 = format_spending_changes("stop:event_476", "EUR", 620.40, 800, events_by_id)
        self.assertEqual(
            res1,
            "Stop the family streaming plan, then pay EUR 620.40 today. This leaves at least EUR 800 available.",
        )

        # Single reduce (request_11)
        res2 = format_spending_changes(
            "reduce_to:event_989:665950", "IDR", 13110000, 34140600, events_by_id
        )
        self.assertEqual(
            res2,
            "Reduce the weekend food delivery to IDR 665,950, then pay IDR 13,110,000 today. This leaves at least IDR 34,140,600 available.",
        )

        # Multiple changes (request_21)
        res3 = format_spending_changes(
            "stop:event_1815|reduce_to:event_1816:23.50", "USD", 1574.40, 1800, events_by_id
        )
        self.assertEqual(
            res3,
            "Stop the online backup subscription and reduce the streaming subscription to USD 23.50, then pay USD 1,574.40 today. This leaves at least USD 1,800 available.",
        )


class TestExplanationTemplateSynthesizer(unittest.TestCase):
    def setUp(self):
        self.synthesizer = ExplanationTemplateSynthesizer()

    def test_synthesize_affordable_now(self):
        profile = UserProfile(
            user_id="user_01",
            home_currency="ZAR",
            current_available_balance=58481.1,
            minimum_balance_to_keep=18000.0,
        )
        request = PurchaseRequest(
            request_id="request_01",
            user_id="user_01",
            request_date="2024-03-03",
            request_type="purchase",
            requested_amount=25256.0,
            desired_completion_date="2024-03-20",
            allows_partial_payment=True,
            request_text="Can I buy the laptop?",
        )
        plan = CandidatePlan(
            payment_method=PaymentMethod.FULL_PAYMENT,
            payment_plan="2024-03-03:25256",
            first_payment_date="2024-03-03",
            total_payable_amount=25256.0,
            number_of_payments=1,
            affordability_status=AffordabilityStatus.AFFORDABLE_NOW,
            earliest_date_for_full_payment="2024-03-03",
            amount_safe_to_pay=25256.0,
        )

        explanation = self.synthesizer.synthesize(plan, profile, request)
        self.assertEqual(
            explanation,
            "Pay ZAR 25,256 today. This leaves at least ZAR 18,000 available over the next 90 days.",
        )

    def test_synthesize_installments(self):
        profile = UserProfile(
            user_id="user_02",
            home_currency="IDR",
            current_available_balance=60383889.2,
            minimum_balance_to_keep=29158400.0,
        )
        request = PurchaseRequest(
            request_id="request_02",
            user_id="user_02",
            request_date="2025-08-05",
            request_type="travel",
            requested_amount=46018000.0,
            desired_completion_date="2025-10-10",
            allows_partial_payment=False,
            request_text="Can I afford the trip?",
        )
        plan = CandidatePlan(
            payment_method=PaymentMethod.INSTALLMENTS,
            payment_plan="2025-08-08:15952906.67|2025-09-07:15952906.67|2025-10-07:15952906.67",
            first_payment_date="2025-08-08",
            total_payable_amount=47858720.01,
            number_of_payments=3,
            affordability_status=AffordabilityStatus.AFFORDABLE_WITH_PLAN,
            earliest_date_for_full_payment="2025-09-15",
            amount_safe_to_pay=17229139.2,
        )

        explanation = self.synthesizer.synthesize(plan, profile, request)
        self.assertEqual(
            explanation,
            "Use 3 installments of IDR 15,952,906.67, starting 8 August 2025. This leaves at least IDR 29,158,400 available.",
        )

    def test_synthesize_wait(self):
        profile = UserProfile(
            user_id="user_03",
            home_currency="IDR",
            current_available_balance=5810300.0,
            minimum_balance_to_keep=2668700.0,
        )
        request = PurchaseRequest(
            request_id="request_03",
            user_id="user_03",
            request_date="2019-09-03",
            request_type="education",
            requested_amount=5491000.0,
            desired_completion_date="2019-11-15",
            allows_partial_payment=False,
            request_text="Should I pay for the course?",
        )
        plan = CandidatePlan(
            payment_method=PaymentMethod.WAIT,
            payment_plan="2019-11-15:5491000",
            first_payment_date="2019-11-15",
            total_payable_amount=5491000.0,
            number_of_payments=1,
            affordability_status=AffordabilityStatus.AFFORDABLE_LATER,
            earliest_date_for_full_payment="2019-11-15",
            amount_safe_to_pay=873000.0,
        )

        explanation = self.synthesizer.synthesize(plan, profile, request)
        self.assertEqual(
            explanation,
            "Pay IDR 5,491,000 in full on 15 November 2019. Paying earlier would take the balance below the IDR 2,668,700 minimum.",
        )

    def test_synthesize_partial_payment(self):
        profile = UserProfile(
            user_id="user_19",
            home_currency="INR",
            current_available_balance=199545.0,
            minimum_balance_to_keep=92800.0,
        )
        request = PurchaseRequest(
            request_id="request_19",
            user_id="user_19",
            request_date="2024-09-04",
            request_type="purchase",
            requested_amount=39660.0,
            desired_completion_date="2024-10-04",
            allows_partial_payment=True,
            request_text="Can I buy the laptop?",
        )
        plan = CandidatePlan(
            payment_method=PaymentMethod.PARTIAL_PAYMENT,
            payment_plan="2024-09-04:28820|2024-09-15:10840",
            first_payment_date="2024-09-04",
            total_payable_amount=39660.0,
            number_of_payments=2,
            affordability_status=AffordabilityStatus.AFFORDABLE_WITH_PLAN,
            earliest_date_for_full_payment="2024-09-15",
            amount_safe_to_pay=28820.0,
        )

        explanation = self.synthesizer.synthesize(plan, profile, request)
        self.assertEqual(
            explanation,
            "Pay INR 28,820 today and the remaining INR 10,840 on 15 September 2024. This completes the full request and keeps the INR 92,800 minimum protected.",
        )


class TestLLMExplanationGenerator(unittest.TestCase):
    def setUp(self):
        self.profile = UserProfile(
            user_id="user_21",
            home_currency="USD",
            current_available_balance=3911.35,
            minimum_balance_to_keep=1800.0,
        )
        self.request = PurchaseRequest(
            request_id="request_21",
            user_id="user_21",
            request_date="2026-04-03",
            request_type="education",
            requested_amount=1574.40,
            desired_completion_date="2026-04-14",
            allows_partial_payment=False,
            request_text="Can I cover the course fee?",
        )
        self.plan = CandidatePlan(
            payment_method=PaymentMethod.FULL_PAYMENT,
            payment_plan="2026-04-03:1574.40",
            first_payment_date="2026-04-03",
            total_payable_amount=1574.40,
            number_of_payments=1,
            affordability_status=AffordabilityStatus.AFFORDABLE_WITH_PLAN,
            earliest_date_for_full_payment="2026-04-15",
            amount_safe_to_pay=1543.35,
            spending_changes_needed="stop:event_1815|reduce_to:event_1816:23.50",
            requires_spending_changes=True,
        )
        self.events_by_id = {
            "event_1815": FinancialEvent(
                event_id="event_1815",
                user_id="user_21",
                event_type="subscription",
                description="Online backup subscription",
                category="cloud_storage",
                direction="debit",
                amount=11.0,
                currency="USD",
                event_date="2026-03-12",
                settlement_date="2026-03-12",
                status="settled",
            ),
            "event_1816": FinancialEvent(
                event_id="event_1816",
                user_id="user_21",
                event_type="subscription",
                description="Streaming subscription",
                category="streaming",
                direction="debit",
                amount=47.0,
                currency="USD",
                event_date="2026-03-09",
                settlement_date="2026-03-09",
                status="settled",
            ),
        }

    def test_fallback_when_groq_api_key_unset(self):
        # Ensure api_key is empty
        generator = LLMExplanationGenerator(api_key="")
        self.assertFalse(generator.is_available)

        # Call with use_llm_for_complex=True - must fall back gracefully to template
        explanation = generator.generate_explanation(
            self.plan,
            self.profile,
            self.request,
            events_by_id=self.events_by_id,
            use_llm_for_complex=True,
        )
        self.assertEqual(
            explanation,
            "Stop the online backup subscription and reduce the streaming subscription to USD 23.50, then pay USD 1,574.40 today. This leaves at least USD 1,800 available.",
        )
        self.assertEqual(generator.total_calls, 0)

    @patch("requests.post")
    def test_llm_call_when_groq_api_key_present(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Stop the online backup subscription and reduce the streaming subscription to USD 23.50, then pay USD 1,574.40 today. This leaves at least USD 1,800 available."
                    }
                }
            ],
            "usage": {"prompt_tokens": 150, "completion_tokens": 35, "total_tokens": 185},
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        generator = LLMExplanationGenerator(api_key="gsk_mock_test_key_123")
        self.assertTrue(generator.is_available)

        explanation = generator.generate_explanation(
            self.plan,
            self.profile,
            self.request,
            events_by_id=self.events_by_id,
            use_llm_for_complex=True,
        )

        self.assertEqual(
            explanation,
            "Stop the online backup subscription and reduce the streaming subscription to USD 23.50, then pay USD 1,574.40 today. This leaves at least USD 1,800 available.",
        )
        self.assertEqual(generator.total_calls, 1)
        self.assertEqual(generator.total_prompt_tokens, 150)
        self.assertEqual(generator.total_completion_tokens, 35)
        self.assertEqual(generator.total_tokens, 185)

        # Verify usage summary
        summary = generator.get_usage_summary()
        self.assertEqual(summary["total_calls"], 1)
        self.assertEqual(summary["total_tokens"], 185)

    @patch("requests.post")
    def test_fallback_on_api_error(self, mock_post):
        # Mock network failure
        mock_post.side_effect = Exception("Groq API rate limit or network error")

        generator = LLMExplanationGenerator(api_key="gsk_mock_test_key_123")
        explanation = generator.generate_explanation(
            self.plan,
            self.profile,
            self.request,
            events_by_id=self.events_by_id,
            use_llm_for_complex=True,
        )

        # Fallback to deterministic template succeeds
        self.assertEqual(
            explanation,
            "Stop the online backup subscription and reduce the streaming subscription to USD 23.50, then pay USD 1,574.40 today. This leaves at least USD 1,800 available.",
        )
        self.assertEqual(generator.failed_calls, 1)


if __name__ == "__main__":
    unittest.main()

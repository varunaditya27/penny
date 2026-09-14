import unittest
from unittest.mock import MagicMock

from backend.core.data.currency import ExchangeRateConverter
from backend.core.data.evidence import EvidenceManager
from backend.core.models.domain import FinancialEvent, PaymentOption, PurchaseRequest, UserProfile
from backend.core.models.results import AffordabilityStatus, PaymentMethod
from backend.core.pipeline import DecisionPipeline
from backend.core.simulation.builder import SimulationLedgerBuilder


class TestDecisionPipeline(unittest.TestCase):
    def setUp(self):
        self.converter = ExchangeRateConverter()
        self.evidence_mgr = EvidenceManager()
        # Initialize pipeline without external LLM network dependency for fast deterministic testing
        self.pipeline = DecisionPipeline(
            evidence_manager=self.evidence_mgr,
            converter=self.converter,
            use_llm=False,
        )
        self.user = UserProfile(
            user_id="user_test_pipeline",
            home_currency="USD",
            current_available_balance=5000.0,
            minimum_balance_to_keep=1000.0,
            payment_methods_user_will_consider={"full_payment", "installments", "partial_payment"},
            max_installment_months=6,
        )
        self.request_date = "2024-03-01"

    def test_salary_stream_stop_income_mutation(self):
        """STOP_INCOME mutation immediately halts recurring salary extraction."""
        hist_events = [
            FinancialEvent(
                event_id="sal_01",
                user_id="user_test_pipeline",
                event_type="income",
                description="Base salary payroll credit",
                category="salary",
                direction="credit",
                amount=4000.0,
                currency="USD",
                event_date="2024-01-25",
                settlement_date="2024-01-25",
                status="settled",
            ),
            FinancialEvent(
                event_id="sal_02",
                user_id="user_test_pipeline",
                event_type="income",
                description="Base salary payroll credit",
                category="salary",
                direction="credit",
                amount=4000.0,
                currency="USD",
                event_date="2024-02-25",
                settlement_date="2024-02-25",
                status="settled",
            ),
        ]

        # Without mutations: ongoing salary is detected
        normal_stream = self.pipeline._extract_recurring_salary_stream(
            user=self.user,
            request_date=self.request_date,
            hist_events=hist_events,
            future_events=[],
            user_mutations=[],
        )
        self.assertIsNotNone(normal_stream)
        self.assertEqual(normal_stream.category, "salary")
        self.assertEqual(normal_stream.day_of_month, 25)
        self.assertEqual(normal_stream.baseline_amount, 4000.0)

        # With STOP_INCOME mutation: returns None
        stop_mutations = [{"action": "STOP_INCOME", "user_id": "user_test_pipeline", "sent_at": "2024-02-28"}]
        stopped_stream = self.pipeline._extract_recurring_salary_stream(
            user=self.user,
            request_date=self.request_date,
            hist_events=hist_events,
            future_events=[],
            user_mutations=stop_mutations,
        )
        self.assertIsNone(stopped_stream)

    def test_scheduled_vs_historical_salary_resolution(self):
        """Future scheduled salary takes precedence over historical salary patterns."""
        hist_events = [
            FinancialEvent(
                event_id="sal_hist_01",
                user_id="user_test_pipeline",
                event_type="income",
                description="Primary household salary",
                category="salary",
                direction="credit",
                amount=3000.0,
                currency="USD",
                event_date="2024-01-15",
                settlement_date="2024-01-15",
                status="settled",
            ),
            FinancialEvent(
                event_id="sal_hist_02",
                user_id="user_test_pipeline",
                event_type="income",
                description="Primary household salary",
                category="salary",
                direction="credit",
                amount=3000.0,
                currency="USD",
                event_date="2024-02-15",
                settlement_date="2024-02-15",
                status="settled",
            ),
        ]

        # Confirmed future scheduled salary on the 20th with raised amount
        future_events = [
            FinancialEvent(
                event_id="sal_sched_01",
                user_id="user_test_pipeline",
                event_type="income",
                description="Next confirmed salary",
                category="salary",
                direction="credit",
                amount=3500.0,
                currency="USD",
                event_date="2024-03-20",
                settlement_date="2024-03-20",
                status="scheduled",
            )
        ]

        stream = self.pipeline._extract_recurring_salary_stream(
            user=self.user,
            request_date=self.request_date,
            hist_events=hist_events,
            future_events=future_events,
            user_mutations=[],
        )

        self.assertIsNotNone(stream)
        # Scheduled salary resolves to day 20 with 3500.0
        self.assertEqual(stream.day_of_month, 20)
        self.assertEqual(stream.baseline_amount, 3500.0)
        self.assertEqual(stream.latest_date, "2024-03-20")

    def test_multi_currency_forex_conversion_in_salary_stream(self):
        """Multi-currency salary streams are converted to user home currency."""
        user_zar = UserProfile(
            user_id="user_zar",
            home_currency="ZAR",
            current_available_balance=20000.0,
            minimum_balance_to_keep=5000.0,
        )

        # Scheduled salary in EUR (EUR -> ZAR published rate is 20.0 in dataset)
        future_events = [
            FinancialEvent(
                event_id="sal_eur_01",
                user_id="user_zar",
                event_type="income",
                description="International employer payroll",
                category="salary",
                direction="credit",
                amount=1000.0,
                currency="EUR",
                event_date="2024-03-15",
                settlement_date="2024-03-15",
                status="scheduled",
            )
        ]

        stream = self.pipeline._extract_recurring_salary_stream(
            user=user_zar,
            request_date=self.request_date,
            hist_events=[],
            future_events=future_events,
            user_mutations=[],
        )

        self.assertIsNotNone(stream)
        self.assertEqual(stream.day_of_month, 15)
        # 1000 EUR * 20 = 20,000 ZAR
        self.assertEqual(stream.baseline_amount, 20000.0)

        # Historical salary in EUR converted to ZAR
        hist_events = [
            FinancialEvent(
                event_id="sal_eur_hist",
                user_id="user_zar",
                event_type="income",
                description="Primary household salary",
                category="salary",
                direction="credit",
                amount=1500.0,
                currency="EUR",
                event_date="2024-02-15",
                settlement_date="2024-02-15",
                status="settled",
            )
        ]
        hist_stream = self.pipeline._extract_recurring_salary_stream(
            user=user_zar,
            request_date=self.request_date,
            hist_events=hist_events,
            future_events=[],
            user_mutations=[],
        )
        self.assertIsNotNone(hist_stream)
        self.assertEqual(hist_stream.baseline_amount, 30000.0)

    def test_seasonal_contract_final_pay_disqualification(self):
        """Final, seasonal, or temporary payroll descriptions disqualify salary recurrence."""
        disqualifying_descriptions = [
            "Final employer payroll",
            "Seasonal contract payment",
            "Temporary assignment pay",
            "Previous employer payroll final settlement",
        ]

        for desc in disqualifying_descriptions:
            hist_events = [
                FinancialEvent(
                    event_id=f"ev_{desc[:6]}",
                    user_id="user_test_pipeline",
                    event_type="income",
                    description=desc,
                    category="salary",
                    direction="credit",
                    amount=2500.0,
                    currency="USD",
                    event_date="2024-02-15",
                    settlement_date="2024-02-15",
                    status="settled",
                )
            ]

            stream = self.pipeline._extract_recurring_salary_stream(
                user=self.user,
                request_date=self.request_date,
                hist_events=hist_events,
                future_events=[],
                user_mutations=[],
            )
            self.assertIsNone(
                stream,
                f"Expected None for disqualifying description '{desc}', got {stream}",
            )

    def test_fallback_path_when_all_options_unaffordable(self):
        """When purchase cannot be afforded by deadline under any option, fallback candidate is selected."""
        poor_user = UserProfile(
            user_id="user_deficit",
            home_currency="USD",
            current_available_balance=100.0,
            minimum_balance_to_keep=100.0,
            payment_methods_user_will_consider={"full_payment", "installments", "partial_payment"},
            max_installment_months=3,
        )

        # Huge purchase request with near deadline and no income
        request = PurchaseRequest(
            request_id="req_unaffordable",
            user_id="user_deficit",
            request_date="2024-03-01",
            request_type="one_time",
            requested_amount=50000.0,
            desired_completion_date="2024-03-05",
            allows_partial_payment=False,
            request_text="Need to buy high-end server",
        )

        options = [
            PaymentOption(
                payment_option_id="opt_1",
                request_id="req_unaffordable",
                payment_method="installments",
                payment_amount=17000.0,
                number_of_payments=3,
                first_payment_date="2024-03-01",
                payment_frequency_days=30,
                financing_fee=1000.0,
                total_payable_amount=51000.0,
            )
        ]

        result = self.pipeline.process_request(
            request=request,
            user=poor_user,
            user_events=[],
            payment_options=options,
        )

        self.assertEqual(result.request_id, "req_unaffordable")
        self.assertEqual(result.affordability_status, AffordabilityStatus.NOT_AFFORDABLE)
        self.assertEqual(result.recommended_payment_method, PaymentMethod.NOT_RECOMMENDED)
        self.assertEqual(result.payment_plan, "none")
        self.assertEqual(result.amount_safe_to_pay, 0.0)

    def test_simulation_ledger_builder_delegation(self):
        """Verifies SimulationLedgerBuilder coordinates filtering, linking, currency, and building."""
        events = [
            # Non-cash event (should be ignored)
            FinancialEvent(
                event_id="nc_01",
                user_id="user_test_pipeline",
                event_type="adjustment",
                description="Stock reward valuation",
                category="investment",
                direction="non_cash",
                amount=10000.0,
                currency="USD",
                event_date="2024-03-05",
                settlement_date="2024-03-05",
                status="settled",
            ),
            # Settled salary
            FinancialEvent(
                event_id="sal_01",
                user_id="user_test_pipeline",
                event_type="income",
                description="Payroll credit",
                category="salary",
                direction="credit",
                amount=5000.0,
                currency="USD",
                event_date="2024-02-15",
                settlement_date="2024-02-15",
                status="settled",
            ),
        ]

        ledger = self.pipeline._build_ledger(
            user=self.user,
            events=events,
            request_date=self.request_date,
            days=90,
        )

        self.assertEqual(len(ledger.balances), 91)
        # Non-cash 10,000 credit must not have inflated balance on 2024-03-05
        bal_mar_05 = ledger.balance_on("2024-03-05")
        self.assertEqual(bal_mar_05, 5000.0)


if __name__ == "__main__":
    unittest.main()

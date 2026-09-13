import os
import tempfile
import unittest
from backend.core.data.currency import ExchangeRateConverter
from backend.core.data.loader import DataLoader
from backend.core.models.domain import CurrencyEnum


class TestExchangeRateConverter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.converter = ExchangeRateConverter("dataset/exchange_rates.csv")

    def test_same_currency(self):
        self.assertEqual(self.converter.convert(1234.5, "USD", "USD", "2024-05-15"), 1234.5)
        self.assertEqual(self.converter.convert(1234.5, "INR", "INR", "2024-05-15"), 1234.5)
        self.assertEqual(self.converter.convert(0.0, "EUR", "USD", "2024-05-15"), 0.0)

    def test_direct_pairs(self):
        # EUR -> USD on 2024-05-15 is directly 1.09
        rate_eur_usd = self.converter.get_rate("EUR", "USD", "2024-05-15")
        self.assertAlmostEqual(rate_eur_usd, 1.09, places=4)
        self.assertEqual(self.converter.get_conversion_path("EUR", "USD", "2024-05-15"), ["EUR", "USD"])

        # USD -> EUR is directly 0.92
        rate_usd_eur = self.converter.get_rate("USD", "EUR", "2024-05-15")
        self.assertAlmostEqual(rate_usd_eur, 0.92, places=4)

        # EUR -> ZAR is directly 20.0
        rate_eur_zar = self.converter.get_rate("EUR", "ZAR", "2024-05-15")
        self.assertAlmostEqual(rate_eur_zar, 20.0, places=4)

        # USD -> IDR is directly 15833.33
        rate_usd_idr = self.converter.get_rate("USD", "IDR", "2024-05-15")
        self.assertAlmostEqual(rate_usd_idr, 15833.33, places=2)

        # USD -> INR is directly 83.33
        rate_usd_inr = self.converter.get_rate("USD", "INR", "2024-05-15")
        self.assertAlmostEqual(rate_usd_inr, 83.33, places=2)

    def test_inverse_pairs(self):
        # ZAR -> EUR: only EUR->ZAR (20.0) exists directly, inverse is 1 / 20.0 = 0.05
        rate_zar_eur = self.converter.get_rate("ZAR", "EUR", "2024-05-15")
        self.assertAlmostEqual(rate_zar_eur, 1.0 / 20.0, places=6)
        self.assertEqual(self.converter.get_conversion_path("ZAR", "EUR", "2024-05-15"), ["ZAR", "EUR"])

        # IDR -> USD: only USD->IDR (15833.33) exists directly, inverse is 1 / 15833.33
        rate_idr_usd = self.converter.get_rate("IDR", "USD", "2024-05-15")
        self.assertAlmostEqual(rate_idr_usd, 1.0 / 15833.33, places=8)

        # INR -> USD: only USD->INR (83.33) exists directly, inverse is 1 / 83.33
        rate_inr_usd = self.converter.get_rate("INR", "USD", "2024-05-15")
        self.assertAlmostEqual(rate_inr_usd, 1.0 / 83.33, places=6)

    def test_triangulation_cross_pairs(self):
        # ZAR -> INR: ZAR -> EUR -> USD -> INR
        # (1 / 20.0) * 1.09 * 83.33 = 4.541485
        rate_zar_inr = self.converter.get_rate("ZAR", "INR", "2024-05-15")
        expected_zar_inr = (1.0 / 20.0) * 1.09 * 83.33
        self.assertAlmostEqual(rate_zar_inr, expected_zar_inr, places=4)
        path = self.converter.get_conversion_path("ZAR", "INR", "2024-05-15")
        self.assertEqual(path, ["ZAR", "EUR", "USD", "INR"])

        # ZAR -> IDR: ZAR -> EUR -> USD -> IDR
        rate_zar_idr = self.converter.get_rate("ZAR", "IDR", "2024-05-15")
        expected_zar_idr = (1.0 / 20.0) * 1.09 * 15833.33
        self.assertAlmostEqual(rate_zar_idr, expected_zar_idr, places=2)

        # INR -> IDR: INR -> USD -> IDR
        rate_inr_idr = self.converter.get_rate("INR", "IDR", "2024-05-15")
        expected_inr_idr = (1.0 / 83.33) * 15833.33
        self.assertAlmostEqual(rate_inr_idr, expected_inr_idr, places=4)

        # IDR -> INR: IDR -> USD -> INR
        rate_idr_inr = self.converter.get_rate("IDR", "INR", "2024-05-15")
        expected_idr_inr = (1.0 / 15833.33) * 83.33
        self.assertAlmostEqual(rate_idr_inr, expected_idr_inr, places=6)

    def test_all_five_currencies_interconvertible(self):
        currencies = ["INR", "IDR", "ZAR", "EUR", "USD"]
        for c1 in currencies:
            for c2 in currencies:
                val = self.converter.convert(100.0, c1, c2, "2024-05-15")
                self.assertGreater(val, 0.0)
                path = self.converter.get_conversion_path(c1, c2, "2024-05-15")
                self.assertEqual(path[0], c1)
                self.assertEqual(path[-1], c2)

    def test_as_of_date_selection(self):
        # Before table date: should pick earliest snapshot (2023-10-15)
        earliest = self.converter.all_dates[0]
        self.assertEqual(self.converter.get_as_of_snapshot_date("2020-01-01"), earliest)

        # Exact match
        self.assertEqual(self.converter.get_as_of_snapshot_date("2024-03-15"), "2024-03-15")

        # Between snapshots: 2024-03-20 should pick 2024-03-15
        self.assertEqual(self.converter.get_as_of_snapshot_date("2024-03-20"), "2024-03-15")

        # After all snapshots: should pick latest snapshot
        latest = self.converter.all_dates[-1]
        self.assertEqual(self.converter.get_as_of_snapshot_date("2030-01-01"), latest)

    def test_dynamic_as_of_rates_with_temp_csv(self):
        csv_data = (
            "rate_date,from_currency,to_currency,rate\n"
            "2024-01-15,USD,EUR,0.90\n"
            "2024-02-15,USD,EUR,0.95\n"
        )
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_data)
            tmp_path = tmp.name

        try:
            custom_converter = ExchangeRateConverter(tmp_path)
            # Predates table: uses earliest (2024-01-15 -> 0.90)
            self.assertAlmostEqual(custom_converter.get_rate("USD", "EUR", "2023-12-01"), 0.90)
            # Exact 2024-01-15
            self.assertAlmostEqual(custom_converter.get_rate("USD", "EUR", "2024-01-15"), 0.90)
            # Between: 2024-02-01 uses 2024-01-15 -> 0.90
            self.assertAlmostEqual(custom_converter.get_rate("USD", "EUR", "2024-02-01"), 0.90)
            # Exact 2024-02-15 uses 2024-02-15 -> 0.95
            self.assertAlmostEqual(custom_converter.get_rate("USD", "EUR", "2024-02-15"), 0.95)
            # After 2024-02-15 uses 2024-02-15 -> 0.95
            self.assertAlmostEqual(custom_converter.get_rate("USD", "EUR", "2024-03-01"), 0.95)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_invalid_currency_rejected(self):
        with self.assertRaises(ValueError):
            self.converter.convert(100.0, "GBP", "USD", "2024-05-15")
        with self.assertRaises(ValueError):
            self.converter.convert(100.0, "USD", "JPY", "2024-05-15")


class TestDataLoader(unittest.TestCase):
    def test_load_profiles(self):
        profiles = DataLoader.load_profiles()
        self.assertEqual(len(profiles), 275)

        # Check user_01
        p1 = profiles["user_01"]
        self.assertEqual(p1.user_id, "user_01")
        self.assertEqual(p1.home_currency, "ZAR")
        self.assertEqual(p1.current_available_balance, 58481.1)
        self.assertEqual(p1.minimum_balance_to_keep, 18000.0)
        self.assertIn("education", p1.financial_priorities)
        self.assertIn("rent", p1.expense_categories_to_protect)
        self.assertIn("dining", p1.expense_categories_user_is_willing_to_reduce)
        self.assertIn("delivery_membership", p1.expense_categories_user_is_willing_to_stop)
        self.assertEqual(p1.payment_methods_user_will_consider, {"full_payment"})
        self.assertIsNone(p1.max_installment_months)

        # Test exclude_sample
        eval_profiles = DataLoader.load_profiles(exclude_sample=True)
        self.assertEqual(len(eval_profiles), 250)
        self.assertNotIn("user_01", eval_profiles)
        self.assertIn("user_26", eval_profiles)

    def test_load_requests(self):
        requests = DataLoader.load_requests()
        self.assertEqual(len(requests), 250)

        # First evaluation request is request_26, user_26
        r0 = requests[0]
        self.assertEqual(r0.request_id, "request_26")
        self.assertEqual(r0.user_id, "user_26")
        self.assertIsInstance(r0.requested_amount, float)
        self.assertIsInstance(r0.allows_partial_payment, bool)

        # Verify sample isolation: no sample user user_01..user_25
        for req in requests:
            self.assertNotIn(req.user_id, DataLoader.SAMPLE_USERS)

    def test_load_requests_sample_isolation_violation(self):
        # Creating a temporary requests CSV that erroneously includes a sample user
        csv_data = (
            "request_id,user_id,request_date,request_type,requested_amount,desired_completion_date,allows_partial_payment,request_text\n"
            "request_999,user_01,2024-03-03,purchase,1000,2024-03-03,false,Buy laptop\n"
        )
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_data)
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError) as ctx:
                DataLoader.load_requests(tmp_path)
            self.assertIn("Sample isolation violation", str(ctx.exception))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_load_sample_requests(self):
        sample_requests = DataLoader.load_sample_requests()
        self.assertEqual(len(sample_requests), 25)

        # All sample requests must belong to sample users
        for req in sample_requests:
            self.assertIn(req.user_id, DataLoader.SAMPLE_USERS)

        r1 = sample_requests[0]
        self.assertEqual(r1.request_id, "request_01")
        self.assertEqual(r1.user_id, "user_01")
        self.assertEqual(r1.requested_amount, 25256.0)

    def test_load_sample_requests_non_sample_violation(self):
        csv_data = (
            "request_id,user_id,request_date,request_type,requested_amount,desired_completion_date,allows_partial_payment,request_text\n"
            "request_999,user_100,2024-03-03,purchase,1000,2024-03-03,false,Buy laptop\n"
        )
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_data)
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError) as ctx:
                DataLoader.load_sample_requests(tmp_path)
            self.assertIn("Sample isolation violation", str(ctx.exception))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_load_sample_ground_truth(self):
        ground_truth = DataLoader.load_sample_ground_truth()
        self.assertEqual(len(ground_truth), 25)
        row1 = ground_truth["request_01"]
        self.assertEqual(row1.request_id, "request_01")
        self.assertEqual(row1.amount_safe_to_pay, 25256.0)
        self.assertEqual(row1.affordability_status, "affordable_now")
        self.assertEqual(row1.recommended_payment_method, "full_payment")
        self.assertEqual(row1.payment_plan, "2024-03-03:25256")
        self.assertEqual(row1.earliest_date_for_full_payment, "2024-03-03")
        self.assertEqual(row1.spending_changes_needed, "none")

    def test_load_events(self):
        # Load all events
        all_events = DataLoader.load_events()
        self.assertEqual(len(all_events), 25342)

        # Filter by user_01
        u1_events = DataLoader.load_events(user_id="user_01")
        self.assertGreater(len(u1_events), 0)
        for e in u1_events:
            self.assertEqual(e.user_id, "user_01")

        # Verify missing amounts parsed as None
        empty_amount_events = [e for e in all_events if e.amount is None]
        self.assertEqual(len(empty_amount_events), 16)
        self.assertEqual(empty_amount_events[0].event_id, "event_253")

        # Exclude sample
        eval_events = DataLoader.load_events(exclude_sample=True)
        for e in eval_events:
            self.assertNotIn(e.user_id, DataLoader.SAMPLE_USERS)

    def test_load_payment_options(self):
        options = DataLoader.load_payment_options()
        self.assertIn("request_01", options)
        req1_opts = options["request_01"]
        self.assertEqual(len(req1_opts), 4)

        opt1 = req1_opts[0]
        self.assertEqual(opt1.payment_option_id, "payment_option_01")
        self.assertEqual(opt1.payment_method, "full_payment")
        self.assertEqual(opt1.payment_amount, 25256.0)
        self.assertEqual(opt1.number_of_payments, 1)
        self.assertEqual(opt1.first_payment_date, "2024-03-03")
        self.assertIsNone(opt1.payment_frequency_days)
        self.assertEqual(opt1.financing_fee, 0.0)
        self.assertEqual(opt1.total_payable_amount, 25256.0)


if __name__ == "__main__":
    unittest.main()

import unittest
from backend.core.data.classifier import IncomeStreamClassifier, IncomeType


class TestIncomeStreamClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IncomeStreamClassifier(use_llm=False)

    def test_confirmed_salaries(self):
        self.assertEqual(self.classifier.classify("Payroll credit"), IncomeType.CONFIRMED_SALARY)
        self.assertEqual(self.classifier.classify("Base salary"), IncomeType.CONFIRMED_SALARY)
        self.assertEqual(self.classifier.classify("International employer payroll"), IncomeType.CONFIRMED_SALARY)
        self.assertTrue(self.classifier.is_recurring_income("Primary household salary"))

    def test_platform_gig_earnings(self):
        self.assertEqual(self.classifier.classify("Delivery platform payout"), IncomeType.RECURRING_PLATFORM_GIG)
        self.assertEqual(self.classifier.classify("Driver platform payout"), IncomeType.RECURRING_PLATFORM_GIG)
        self.assertEqual(self.classifier.classify("Weekly app earnings"), IncomeType.RECURRING_PLATFORM_GIG)
        self.assertFalse(self.classifier.is_recurring_income("Task marketplace payout"))

    def test_freelance_contracts(self):
        self.assertEqual(self.classifier.classify("Website project payment"), IncomeType.RECURRING_CONTRACT)
        self.assertEqual(self.classifier.classify("Client retainer payment"), IncomeType.RECURRING_CONTRACT)
        self.assertTrue(self.classifier.is_recurring_income("Consulting invoice payment"))

    def test_terminated_or_temporary(self):
        self.assertEqual(self.classifier.classify("Previous employer payroll"), IncomeType.TERMINATED_SALARY)
        self.assertEqual(self.classifier.classify("Final employer payroll"), IncomeType.TERMINATED_SALARY)
        self.assertEqual(self.classifier.classify("Temporary assignment pay"), IncomeType.TERMINATED_SALARY)
        self.assertFalse(self.classifier.is_recurring_income("Final employer payroll"))

    def test_excluded_windfalls(self):
        self.assertEqual(self.classifier.classify("Quarterly performance bonus"), IncomeType.EXCLUDED_WINDFALL)
        self.assertEqual(self.classifier.classify("Account commission payment"), IncomeType.EXCLUDED_WINDFALL)
        self.assertEqual(self.classifier.classify("Prize proceeds"), IncomeType.EXCLUDED_WINDFALL)
        self.assertEqual(self.classifier.classify("Pending merchant refund"), IncomeType.EXCLUDED_WINDFALL)
        self.assertFalse(self.classifier.is_recurring_income("Performance commission"))
        self.assertFalse(self.classifier.is_recurring_income("Investment sale proceeds"))

    def test_fallback_keywords(self):
        self.assertEqual(self.classifier.classify("Unusual monthly bonus check"), IncomeType.EXCLUDED_WINDFALL)
        self.assertEqual(self.classifier.classify("Random monthly lottery winning"), IncomeType.EXCLUDED_WINDFALL)
        self.assertEqual(self.classifier.classify("Corporate monthly wage transfer"), IncomeType.CONFIRMED_SALARY)


if __name__ == "__main__":
    unittest.main()

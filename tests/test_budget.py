import unittest
from reverse_check.budget import Budget
from reverse_check.http_source import FetchError


class BudgetTests(unittest.TestCase):
    def test_deadline_and_shared_cleanup(self):
        ticks = [0.0]
        budget = Budget(10, clock=lambda: ticks[0])
        ticks[0] = 8
        self.assertEqual(budget.timeout_for(20), 2)
        ticks[0] = 10
        with self.assertRaises(FetchError) as caught: budget.timeout_for(20)
        self.assertEqual(caught.exception.status, 'budget_exhausted')
        self.assertEqual(budget.cleanup_timeout(), 5)
        ticks[0] = 13
        budget.stop()
        self.assertEqual(budget.cleanup_timeout(), 2)
        ticks[0] = 15
        with self.assertRaises(FetchError): budget.cleanup_timeout()

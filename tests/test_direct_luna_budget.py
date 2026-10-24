"""Focused regression for the Steward-authorized total Luna allocation."""

import unittest

from riverview_core.resident_execution.direct_luna import (
    ADDITIONAL_LIMIT,
    BASELINE_TOTAL,
    TOTAL_CREDIT,
)


class DirectLunaBudgetTests(unittest.TestCase):
    def test_remaining_allocation_includes_prior_experiment_spending(self):
        self.assertEqual(BASELINE_TOTAL, 0.04104010)
        self.assertEqual(TOTAL_CREDIT, 5.0)
        self.assertEqual(ADDITIONAL_LIMIT, 4.95895990)
        self.assertEqual(BASELINE_TOTAL + ADDITIONAL_LIMIT, TOTAL_CREDIT)


if __name__ == "__main__":
    unittest.main()

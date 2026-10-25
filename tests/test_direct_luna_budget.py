# File Revision: 1.0.0
"""Focused regression for the Steward-authorized total Luna allocation."""

import unittest

from riverview_core.resident_execution.direct_luna import (
    ADDITIONAL_LIMIT,
    BASELINE_TOTAL,
    MAX_OUTPUT_TOKENS,
    TOTAL_CREDIT,
    _response_ids,
    _safe_failure_detail,
)
from uuid import uuid4


class DirectLunaBudgetTests(unittest.TestCase):
    def test_remaining_allocation_includes_prior_experiment_spending(self):
        self.assertEqual(BASELINE_TOTAL, 0.04104010)
        self.assertEqual(TOTAL_CREDIT, 5.0)
        self.assertEqual(ADDITIONAL_LIMIT, 4.95895990)
        self.assertEqual(BASELINE_TOTAL + ADDITIONAL_LIMIT, TOTAL_CREDIT)

    def test_uuid_response_idempotency_bug_is_reproduced_and_normalized(self):
        request_id, correlation_id = uuid4(), uuid4()
        with self.assertRaisesRegex(TypeError, "concatenate str"):
            "luna:" + request_id
        normalized = _response_ids({"request_id": request_id,
                                    "correlation_id": correlation_id})
        self.assertEqual(normalized, (str(request_id), str(correlation_id)))
        self.assertEqual("luna:" + normalized[0], "luna:" + str(request_id))

    def test_failure_detail_is_bounded_and_redacts_credentials(self):
        detail = _safe_failure_detail(TypeError(
            "can only concatenate str (not 'UUID') to str; api_key=sk-abcdefghijklmno"))
        self.assertIn("TypeError", detail)
        self.assertIn("UUID", detail)
        self.assertNotIn("sk-abcdefghijklmno", detail)
        self.assertLessEqual(len(detail), 220)
        self.assertNotIn("\n", detail)

    def test_typed_supervision_has_room_for_advisory_output(self):
        self.assertEqual(MAX_OUTPUT_TOKENS, 4096)


if __name__ == "__main__":
    unittest.main()

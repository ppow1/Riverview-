# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_role_context.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.2
# Purpose: Verify stable Grace office identity is shared and cannot imply permissions
# Execution Model: Request-driven unit test
# Observability: Assertion results; no external resources
# Dependencies: Python standard library; Grace role-context builder
# Authority: No database, credential, network or production access
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Add stable Director of Operations identity contract tests
# Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-GUIDANCE-001 | Require actionable Engineering proposal behavior without granting authority
# Contracts: docs/architecture/GRACE_DIRECTOR_OF_OPERATIONS_RECONCILIATION.md
# Tests: python3 -m unittest tests.test_grace_role_context
# History: Git and revision/backup manifest
# =============================================================================
"""Fast checks for Grace's stable role context across model implementations."""

import unittest

from riverview_core.resident_execution.grace_role_context import (
    ROLE_CONTEXT_REVISION, build_grace_role_context,
)


class GraceRoleContextTests(unittest.TestCase):
    def test_context_names_one_operations_office_and_preserves_authority_boundary(self):
        context = build_grace_role_context()
        self.assertEqual(ROLE_CONTEXT_REVISION, "1.1.2")
        self.assertIn("You are Grace", context)
        self.assertIn("Director of Operations", context)
        self.assertIn("Alfred is the separate Chief of Staff", context)
        self.assertIn("Steward retains final institutional authority", context)
        self.assertIn("Continuous Momentum Engine (CME)", context)
        self.assertIn("0.6B autonomic, 30B vision, and 80B reasoning", context)
        self.assertIn("this role description grants no permission", context)
        self.assertNotIn("Chief of Staff of Engineering", context)
        self.assertNotIn("AI director of engineering", context)

    def test_concrete_engineering_request_gets_proposal_without_invented_prerequisites(self):
        context = build_grace_role_context()
        self.assertIn("state a proposed assignment in the response", context)
        self.assertIn("five concise bullets, at most 120 words total", context)
        self.assertIn("measurable acceptance criteria", context)
        self.assertIn("do not refuse to propose", context)
        self.assertIn("does not create records, approve authority, or dispatch work", context)
        self.assertIn("objective.submit", context)
        self.assertIn("Do not invent prerequisites", context)


if __name__ == "__main__":
    unittest.main()

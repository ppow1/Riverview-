# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_role_context.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.0
# Purpose: Verify stable Grace office identity is shared and cannot imply permissions
# Execution Model: Request-driven unit test
# Observability: Assertion results; no external resources
# Dependencies: Python standard library; Grace role-context builder
# Authority: No database, credential, network or production access
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Add stable Director of Operations identity contract tests
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
        self.assertEqual(ROLE_CONTEXT_REVISION, "1.0.0")
        self.assertIn("You are Grace", context)
        self.assertIn("Director of Operations", context)
        self.assertIn("Alfred is the separate Chief of Staff", context)
        self.assertIn("Steward retains final institutional authority", context)
        self.assertIn("Continuous Momentum Engine (CME)", context)
        self.assertIn("0.6B autonomic, 30B vision, and 80B reasoning", context)
        self.assertIn("this role description grants no permission", context)
        self.assertNotIn("Chief of Staff of Engineering", context)
        self.assertNotIn("AI director of engineering", context)


if __name__ == "__main__":
    unittest.main()

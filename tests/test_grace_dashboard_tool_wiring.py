# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_dashboard_tool_wiring.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.0
# Purpose: Verify the production dashboard Grace router receives the internal Comms5 tool adapter
# Execution Model: Isolated provider doubles and a patched fixed adapter constructor
# Observability: Asserts adapter construction and router binding
# Dependencies: status_dashboard.server; GraceInternalTools; GraceModelRouter
# Authority: No network or database access
# Tests: python3 -m unittest tests.test_grace_dashboard_tool_wiring
# History: New file; no predecessor
# =============================================================================
"""Ensure the live dashboard router is wired to Grace's internal operations."""

import unittest
from unittest.mock import patch

from riverview_core.status_dashboard.server import _build_grace_model_router


class Provider:
    def __init__(self, name):
        self.model = name
        self.model_sha256 = "a" * 64
        self.provider_id = "test." + name


class GraceDashboardToolWiringTests(unittest.TestCase):
    @patch("riverview_core.resident_execution.internal_tools.GraceInternalTools")
    def test_dashboard_router_constructs_and_receives_internal_tools(self, factory):
        tools = object()
        factory.return_value = tools
        router = _build_grace_model_router(
            autonomic=Provider("0.6B"), vision=Provider("30B"),
            reasoning=Provider("80B"))
        factory.assert_called_once_with()
        self.assertIs(router.internal_tools, tools)


if __name__ == "__main__":
    unittest.main()

# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_linux_browser_runner.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Verify browser runner target and path safety rules
# Execution Model: Local unit test
# Observability: Pytest assertions
# Dependencies: Python 3.10+; scripts.run_linux_browser_acceptance
# Authority: No network access or production state
# Changed: 2026-10-18 UTC | RV-LINUX-BROWSER-ACCEPTANCE-001 | Add runner safety tests
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/test_linux_browser_runner.py
# History: Git
# =============================================================================
"""Unit tests for browser target and request-path bounds."""

import unittest

from scripts.run_linux_browser_acceptance import validate_smoke_path, validate_target


class BrowserRunnerSafetyTest(unittest.TestCase):
    def test_loopback_targets_are_allowed_without_remote_opt_in(self):
        for target in ("http://localhost:8766", "https://127.0.0.1", "http://[::1]:8766"):
            with self.subTest(target=target):
                origin, _ = validate_target(target, allow_remote=False)
                self.assertTrue(origin.startswith(("http://", "https://")))

    def test_unsafe_or_remote_targets_fail_closed(self):
        for target in (
            "https://example.invalid", "https://user:pass@example.invalid", "https://example.invalid/path",
            "https://example.invalid/?token=secret", "file:///tmp/page.html", "http://example.invalid#fragment",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_target(target, allow_remote=False)

    def test_remote_read_only_target_requires_explicit_opt_in(self):
        origin, host = validate_target("https://staging.example.invalid", allow_remote=True)
        self.assertEqual(origin, "https://staging.example.invalid")
        self.assertEqual(host, "staging.example.invalid")

    def test_smoke_path_accepts_simple_absolute_paths(self):
        for path in ("/", "/health", "/a/b"):
            with self.subTest(path=path):
                self.assertEqual(validate_smoke_path(path), path)

    def test_smoke_path_rejects_non_origin_or_query_targets(self):
        for path in ("", "health", "//outside.invalid", "/?secret=1", "/#section", "/bad\\path"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_smoke_path(path)

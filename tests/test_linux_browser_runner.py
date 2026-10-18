# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_linux_browser_runner.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.3
# Purpose: Verify browser runner and authenticated staging state safety rules
# Execution Model: Local unit test
# Observability: Pytest assertions
# Dependencies: Python 3.10+; scripts.run_linux_browser_acceptance
# Authority: No network access or production state
# Changed: 2026-10-18 UTC | RV-C2-STAGING-GRACE-BROWSER-003 | Add staging bridge fail-closed tests
# Contracts: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
# Tests: tests/test_linux_browser_runner.py
# History: Git
# =============================================================================
"""Unit tests for browser target and request-path bounds."""

import unittest
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from scripts.grace_staging_browser import (
    STAGING_CONFIRMATION,
    validate_grace_staging_config,
    validate_storage_state,
)
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


class GraceStagingBrowserGuardTests(unittest.TestCase):
    conversation_id = "00000000-0000-4000-8000-000000000001"

    def _state(self, directory: str, domain: str, *, origins=None, mode=0o600) -> str:
        path = Path(directory) / "storage-state.json"
        path.write_text(json.dumps({"cookies": [{"name": "synthetic-test-cookie",
                                                   "value": "test-only",
                                                   "domain": domain}],
                                    "origins": [] if origins is None else origins}),
                        encoding="utf-8")
        path.chmod(mode)
        return str(path)

    def test_disposable_loopback_requires_ack_and_host_scoped_cookie_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self._state(directory, "127.0.0.1")
            config = {"base_url": "http://127.0.0.1:8877",
                      "configured_origin": "http://127.0.0.1:8877",
                      "storage_state": state,
                      "test_account_label": "synthetic-steward@example.test",
                      "conversation_id": self.conversation_id,
                      "seed_message_text": "Harmless staging test request.",
                      "confirmation": STAGING_CONFIRMATION,
                      "allow_remote": False}
            self.assertEqual(validate_grace_staging_config(**config)[0], "http://127.0.0.1:8877")
            config["confirmation"] = ""
            with self.assertRaisesRegex(ValueError, "loopback_requires_disposable"):
                validate_grace_staging_config(**config)

    def test_remote_requires_https_staging_name_explicit_opt_in_and_exact_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self._state(directory, "grace-staging.example.invalid")
            config = {"base_url": "https://grace-staging.example.invalid",
                      "configured_origin": "https://grace-staging.example.invalid",
                      "storage_state": state, "test_account_label": "synthetic-steward",
                      "conversation_id": self.conversation_id,
                      "seed_message_text": "Harmless staging test request.", "confirmation": "",
                      "allow_remote": True}
            self.assertEqual(validate_grace_staging_config(**config)[1], "grace-staging.example.invalid")
            config["base_url"] = "https://grace.example.invalid"
            config["configured_origin"] = config["base_url"]
            with self.assertRaisesRegex(ValueError, "remote_target_must_be_https_staging_host"):
                validate_grace_staging_config(**config)

    def test_rejects_cookie_for_other_host_or_storage_state_with_local_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            wrong_host = self._state(directory, "example.invalid")
            with self.assertRaisesRegex(ValueError, "cookie_host_mismatch"):
                validate_storage_state(wrong_host, expected_host="grace-staging.example.invalid")
            local_storage = self._state(directory, "grace-staging.example.invalid",
                                        origins=[{"origin": "https://grace-staging.example.invalid",
                                                  "localStorage": [{"name": "token", "value": "secret"}]}])
            with self.assertRaisesRegex(ValueError, "local_storage_forbidden"):
                validate_storage_state(local_storage, expected_host="grace-staging.example.invalid")

    def test_rejects_permissive_storage_file_and_staging_origin_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self._state(directory, "grace-staging.example.invalid", mode=0o644)
            with self.assertRaisesRegex(ValueError, "permissions_or_type_invalid"):
                validate_storage_state(state, expected_host="grace-staging.example.invalid")
            state = self._state(directory, "grace-staging.example.invalid")
            config = {"base_url": "https://grace-staging.example.invalid",
                      "configured_origin": "https://other-staging.example.invalid",
                      "storage_state": state, "test_account_label": "synthetic-steward",
                      "conversation_id": self.conversation_id,
                      "seed_message_text": "Harmless staging test request.", "confirmation": "",
                      "allow_remote": True}
            with self.assertRaisesRegex(ValueError, "staging_origin_mismatch"):
                validate_grace_staging_config(**config)

    def test_staging_runner_rejects_missing_environment_before_browser_launch(self):
        env = os.environ.copy()
        for key in (
            "RIVERVIEW_GRACE_STAGING_ORIGIN",
            "RIVERVIEW_GRACE_STAGING_STORAGE_STATE",
            "RIVERVIEW_GRACE_STAGING_TEST_ACCOUNT_LABEL",
            "RIVERVIEW_GRACE_STAGING_CONVERSATION_ID",
            "RIVERVIEW_GRACE_STAGING_SEED_MESSAGE_TEXT",
            "RIVERVIEW_GRACE_STAGING_CONFIRMATION",
        ):
            env.pop(key, None)
        runner = Path(__file__).resolve().parents[1] / "scripts/run_linux_browser_acceptance.py"
        result = subprocess.run(
            [sys.executable, str(runner), "--grace-staging-readonly",
             "--base-url", "http://127.0.0.1:8877"],
            cwd=runner.parents[1], env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("staging_origin_required", result.stderr)
        self.assertNotIn("browser_acceptance_target=", result.stdout)

# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_browser_status_projection.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Verify safe browser status projection, freshness, failure state, and schema boundary
# Execution Model: Deterministic unit tests with temporary local evidence only
# Observability: unittest result counts and assertions over sanitized JSON
# Dependencies: Python standard library; jsonschema test dependency
# Authority: Synthetic local evidence; no browser/network/production access
# Changed: 2026-10-18 UTC | RV-C2-BROWSER-STATUS-001 | Cover private output and evidence directory boundaries
# Contracts: docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.md; docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.schema.json
# Tests: This file
# History: Git and revision/backup manifest
# =============================================================================
"""Contract tests for the local-only browser run status projection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from scripts.browser_status_projection import build_status, project_directory, write_status

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "0123456789abcdef0123456789abcdef01234567"
NOW = datetime(2026, 10, 18, 18, 30, tzinfo=timezone.utc)
SCHEMA = json.loads((ROOT / "docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.schema.json").read_text())


def validate(status: dict) -> None:
    Draft202012Validator(SCHEMA).validate(status)


class BrowserStatusProjectionTests(unittest.TestCase):
    def test_passed_local_run_has_stable_identity_freshness_and_safe_diagnostic(self):
        start = {"mode": "read-only-smoke", "target_origin": "http://127.0.0.1:8877",
                 "started_at": "2026-10-18T18:25:00Z", "evidence_directory": "/private/user/path"}
        result = {"status": "PASS", "exit_code": 0, "completed_at": "2026-10-18T18:26:00Z",
                  "target_host": "127.0.0.1", "command": "contains private path"}
        errors = {"passed": 2, "failed": 0, "skipped": 2}
        status = build_status(source_commit=COMMIT, observed_at=NOW, run_start=start,
                              runner_result=result, errors=errors)
        validate(status)
        self.assertEqual(status["run_status"], "passed")
        self.assertEqual(status["freshness"], "current")
        self.assertEqual(status["environment"], "local_loopback")
        self.assertRegex(status["run_id"], r"^rvba-[0-9a-f]{20}$")
        self.assertEqual(status["diagnostic_ref"], "docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.md")
        serialized = json.dumps(status)
        for private in ("127.0.0.1", "8877", "/private/user/path", "contains private path"):
            self.assertNotIn(private, serialized)

    def test_blocked_run_uses_only_allowlisted_error_kind_and_omits_private_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run-start.json").write_text(json.dumps({
                "mode": "grace-staging-readonly", "target_origin": "http://localhost:8877",
                "started_at": "2026-10-18T18:25:00Z", "seed_message": "private conversation"}))
            (root / "runner-result.json").write_text(json.dumps({
                "status": "FAIL", "exit_code": 1, "completed_at": "2026-10-18T18:26:00Z",
                "target_host": "localhost", "private_value": "secret"}))
            (root / "browser-errors.json").write_text(json.dumps({
                "passed": 1, "failed": 1, "skipped": 0, "private": "secret"}))
            (root / "test.errors.json").write_text(json.dumps({"errors": [
                {"kind": "blocked_non_get", "message": "private conversation text",
                 "url": "https://private.invalid/path?token=secret"}]}))
            status = project_directory(root, source_commit=COMMIT, observed_at=NOW)
            validate(status)
            self.assertEqual(status["run_status"], "blocked")
            self.assertEqual(status["failure_category"], "blocked_non_get")
            self.assertEqual(status["counts"], {"passed": 1, "failed": 1, "skipped": 0})
            for private in ("private conversation", "private.invalid", "token=secret", "private_value"):
                self.assertNotIn(private, json.dumps(status))
            output = root / "browser-status.json"
            write_status(output, status)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            validate(json.loads(output.read_text()))

    def test_stale_result_is_not_promoted_to_current(self):
        start = {"mode": "read-only-smoke", "target_origin": "http://localhost:8877",
                 "started_at": "2026-10-18T18:00:00Z"}
        result = {"status": "PASS", "exit_code": 0, "completed_at": "2026-10-18T18:00:00Z"}
        status = build_status(source_commit=COMMIT, observed_at=NOW, run_start=start,
                              runner_result=result, errors={"passed": 1})
        validate(status)
        self.assertEqual(status["run_status"], "passed")
        self.assertEqual(status["freshness"], "stale")

    def test_running_and_explicit_prerequisite_states_are_distinct(self):
        start = {"mode": "read-only-smoke", "target_origin": "http://[::1]:8877",
                 "started_at": "2026-10-18T18:29:00Z"}
        running = build_status(source_commit=COMMIT, observed_at=NOW, run_start=start)
        validate(running)
        self.assertEqual((running["run_status"], running["freshness"]), ("running", "current"))
        blocked = build_status(source_commit=COMMIT, observed_at=NOW, state="blocked")
        staging = build_status(source_commit=COMMIT, observed_at=NOW, state="staging_not_available")
        validate(blocked); validate(staging)
        self.assertEqual((blocked["run_status"], blocked["failure_category"]),
                         ("blocked", "unknown"))
        self.assertEqual((staging["run_status"], staging["failure_category"], staging["environment"]),
                         ("staging_not_available", "staging_target_unavailable", "staging"))
        self.assertIsNone(staging["run_id"])

    def test_remote_target_is_blocked_without_disclosing_target(self):
        start = {"mode": "read-only-smoke", "target_origin": "https://prod.example.invalid/private/path",
                 "started_at": "2026-10-18T18:25:00Z"}
        status = build_status(source_commit=COMMIT, observed_at=NOW, run_start=start,
                              runner_result={"status": "PASS", "exit_code": 0}, errors={"passed": 1})
        validate(status)
        self.assertEqual(status["run_status"], "blocked")
        self.assertEqual(status["failure_category"], "unsupported_remote_target")
        self.assertNotIn("prod.example.invalid", json.dumps(status))
        self.assertIsNone(status["run_id"])

    def test_rejects_invalid_commit_and_naive_time(self):
        with self.assertRaisesRegex(ValueError, "source_commit_must_be_full_git_sha"):
            build_status(source_commit="short")
        with self.assertRaisesRegex(ValueError, "observed_at_must_be_timezone_aware"):
            build_status(source_commit=COMMIT, observed_at=datetime(2026, 10, 18))

    def test_unknown_fields_are_not_allowed_by_public_contract(self):
        status = build_status(source_commit=COMMIT, observed_at=NOW, state="staging_not_available")
        status["private_target_url"] = "https://secret.invalid"
        with self.assertRaises(ValidationError):
            validate(status)

    def test_output_requires_private_directory_without_changing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "shared"
            parent.mkdir(mode=0o755)
            os.chmod(parent, 0o755)
            with self.assertRaisesRegex(ValueError, "status_output_parent_must_be_private"):
                write_status(parent / "status.json", build_status(
                    source_commit=COMMIT, observed_at=NOW, state="blocked"))
            self.assertEqual(parent.stat().st_mode & 0o777, 0o755)
            self.assertFalse((parent / "status.json").exists())

    def test_evidence_root_must_be_a_real_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file_path = root / "not-a-directory"
            file_path.write_text("safe")
            link = root / "link"
            link.symlink_to(file_path)
            for candidate in (file_path, link):
                with self.assertRaisesRegex(ValueError, "evidence_directory_must_be_real_directory"):
                    project_directory(candidate, source_commit=COMMIT, observed_at=NOW)


if __name__ == "__main__":
    unittest.main()

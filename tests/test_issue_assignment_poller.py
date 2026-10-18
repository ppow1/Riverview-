# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_issue_assignment_poller.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Purpose: Verify inert issue polling, durable receipts, concurrency, failure, and retry behavior
# Execution Model: Isolated request-driven tests using temporary directories and fake GitHub data
# Observability: unittest results; fixture bodies are never emitted in receipts
# Dependencies: Python 3.10+; unittest
# Authority: No network calls, credentials, session control, or production paths
# Changed: 2026-10-18 UTC | RV-W1-ISSUE-POLL-001 | Cover the opt-in issue comment polling prototype.
# Contracts: docs/components/WORK_REGISTRY.md
# Tests: This file
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Isolated tests for the read-only GitHub issue polling prototype."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
import unittest
from unittest.mock import patch

from scripts.poll_issue_assignments import (
    PollError, _gh_endpoint, fetch_issue_comments, poll_once, watch,
)


T0 = datetime(2026, 10, 18, 18, 0, tzinfo=timezone.utc)


def comment(identifier, body="W1 assignment; inert fixture", *, updated="18:00"):
    stamp = f"2026-10-18T{updated}:00Z"
    return {"id": identifier,
            "html_url": f"https://github.com/ppow1/Riverview-/issues/120#issuecomment-{identifier}",
            "user": "steward", "created_at": stamp, "updated_at": stamp,
            "body": body}


class IssueAssignmentPollerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.state = Path(self.directory.name) / "receipts.json"

    def tearDown(self):
        self.directory.cleanup()

    def test_first_poll_persists_only_metadata_and_body_digest(self):
        raw = comment(1001, "secret: DO-NOT-PERSIST-OR-PRINT")
        result = poll_once(state_path=self.state, fetcher=lambda *_: [raw], now=lambda: T0)
        saved = self.state.read_text(encoding="utf-8")
        document = json.loads(saved)
        receipt = document["comments"]["1001"]
        self.assertEqual(result["receipt_changes"][0]["change"], "discovered")
        self.assertEqual(receipt["versions"][0]["body_sha256"],
                         hashlib.sha256(raw["body"].encode()).hexdigest())
        self.assertEqual(document["cursor_updated_at"], "2026-10-18T18:00:00Z")
        self.assertNotIn(raw["body"], saved)
        self.assertNotIn("DO-NOT-PERSIST-OR-PRINT", json.dumps(result))
        self.assertNotIn("prompts", document)
        self.assertFalse(self.state.with_name(self.state.name + ".lock").exists())

    def test_repeated_poll_is_idempotent_and_replay_safe(self):
        raw = comment(1002)
        first = poll_once(state_path=self.state, fetcher=lambda *_: [raw], now=lambda: T0)
        second = poll_once(state_path=self.state, fetcher=lambda *_: [raw],
                           now=lambda: T0.replace(minute=1))
        self.assertEqual(first["stored_comment_count"], 1)
        self.assertEqual(second["receipt_changes"], [])
        self.assertEqual(len(json.loads(self.state.read_text())["comments"]["1002"]["versions"]), 1)

    def test_comment_edit_is_recorded_as_a_new_digest_version(self):
        first = comment(1003, "first assignment")
        changed = comment(1003, "edited assignment", updated="18:01")
        poll_once(state_path=self.state, fetcher=lambda *_: [first], now=lambda: T0)
        result = poll_once(state_path=self.state, fetcher=lambda *_: [changed],
                           now=lambda: T0.replace(minute=2))
        versions = json.loads(self.state.read_text())["comments"]["1003"]["versions"]
        self.assertEqual(result["receipt_changes"][0]["change"], "edited")
        self.assertEqual(len(versions), 2)
        self.assertNotEqual(versions[0]["body_sha256"], versions[1]["body_sha256"])
        self.assertNotIn("edited assignment", self.state.read_text())

    def test_cursor_uses_overlap_and_advances_only_after_success(self):
        raw = comment(1004)
        seen = []
        def fetcher(_repo, _issue, since):
            seen.append(since)
            if len(seen) == 2:
                raise PollError("github_api_failed")
            return [raw]
        poll_once(state_path=self.state, fetcher=fetcher, now=lambda: T0)
        with self.assertRaisesRegex(PollError, "github_api_failed"):
            poll_once(state_path=self.state, fetcher=fetcher,
                      now=lambda: T0.replace(minute=10))
        after_failure = json.loads(self.state.read_text())["last_successful_poll_at"]
        self.assertEqual(after_failure, "2026-10-18T18:00:00Z")
        self.assertEqual(seen[1], datetime(2026, 10, 18, 17, 55, tzinfo=timezone.utc))

    def test_concurrent_process_threads_do_not_lose_receipts(self):
        comments = [comment(1100 + number) for number in range(12)]
        def run(item):
            return poll_once(state_path=self.state, fetcher=lambda *_: [item], now=lambda: T0)
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(run, comments))
        document = json.loads(self.state.read_text())
        self.assertEqual(set(document["comments"]),
                         {str(item["id"]) for item in comments})

    def test_concurrent_process_writers_do_not_lose_receipts(self):
        code = r'''import json,sys
from pathlib import Path
from scripts.poll_issue_assignments import poll_once
identifier=int(sys.argv[2])
item={"id":identifier,"html_url":f"https://github.com/ppow1/Riverview-/issues/120#issuecomment-{identifier}","user":"steward","created_at":"2026-10-18T18:00:00Z","updated_at":"2026-10-18T18:00:00Z","body":f"fixture {identifier}"}
def fetcher(*_): return [item]
print(json.dumps(poll_once(state_path=Path(sys.argv[1]),fetcher=fetcher)))
'''
        def invoke(identifier):
            result = subprocess.run([sys.executable, "-c", code, str(self.state),
                                     str(identifier)], check=True, capture_output=True,
                                    text=True, timeout=20)
            return json.loads(result.stdout)
        identifiers = list(range(1200, 1208))
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(invoke, identifiers))
        stored = json.loads(self.state.read_text(encoding="utf-8"))["comments"]
        self.assertEqual(set(stored), {str(value) for value in identifiers})

    def test_failed_fetch_leaves_no_state_and_does_not_echo_response(self):
        with self.assertRaisesRegex(PollError, "github_api_failed"):
            poll_once(state_path=self.state,
                      fetcher=lambda *_: (_ for _ in ()).throw(PollError("github_api_failed")),
                      now=lambda: T0)
        self.assertFalse(self.state.exists())

    def test_atomic_write_failure_is_replayed_after_restart(self):
        raw = comment(1007)
        with patch("scripts.poll_issue_assignments._write_atomic",
                   side_effect=OSError("fixture failure")):
            with self.assertRaises(OSError):
                poll_once(state_path=self.state, fetcher=lambda *_: [raw], now=lambda: T0)
        self.assertFalse(self.state.exists())
        replay = poll_once(state_path=self.state, fetcher=lambda *_: [raw],
                           now=lambda: T0.replace(minute=1))
        self.assertEqual(replay["receipt_changes"][0]["change"], "discovered")
        self.assertEqual(replay["stored_comment_count"], 1)

    def test_crash_left_stale_lock_is_recovered_after_threshold(self):
        lock = self.state.with_name(self.state.name + ".lock")
        lock.mkdir()
        old = time.time() - 301
        os.utime(lock, (old, old))
        result = poll_once(state_path=self.state, fetcher=lambda *_: [comment(1008)],
                           now=lambda: T0)
        self.assertEqual(result["stored_comment_count"], 1)
        self.assertFalse(lock.exists())

    def test_untrusted_or_wrong_target_comment_is_rejected(self):
        invalid = comment(1005)
        invalid["html_url"] = "https://example.invalid/inject"
        with self.assertRaisesRegex(PollError, "comment_url_invalid"):
            poll_once(state_path=self.state, fetcher=lambda *_: [invalid], now=lambda: T0)
        self.assertFalse(self.state.exists())

    def test_deleted_comment_author_remains_unknown_without_invented_identity(self):
        raw = comment(1009)
        raw["user"] = None
        poll_once(state_path=self.state, fetcher=lambda *_: [raw], now=lambda: T0)
        self.assertIsNone(json.loads(self.state.read_text())["comments"]["1009"]["author"])

    def test_invalid_receipt_state_fails_closed_without_overwrite(self):
        original = json.dumps({"schema_version": "rv.issue-comment-receipts.v1",
                               "repository": "ppow1/Riverview-", "issue_number": 120,
                               "last_successful_poll_at": None, "cursor_updated_at": None,
                               "comments": {"1010": {"url": "invalid", "versions": []}}})
        self.state.write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(PollError, "receipt_comment_record_invalid"):
            poll_once(state_path=self.state, fetcher=lambda *_: [], now=lambda: T0)
        self.assertEqual(self.state.read_text(encoding="utf-8"), original)

    def test_gh_request_uses_validated_read_only_comment_endpoint(self):
        endpoint = _gh_endpoint("ppow1/Riverview-", 120, T0)
        self.assertTrue(endpoint.startswith("repos/ppow1/Riverview-/issues/120/comments?"))
        self.assertIn("since=2026-10-18T18%3A00%3A00Z", endpoint)
        self.assertEqual(_gh_endpoint("ppow1/Riverview-", 120).split("?")[0],
                         "repos/ppow1/Riverview-/issues/120/comments")
        with patch("scripts.poll_issue_assignments.subprocess.run") as run:
            run.return_value.stdout = json.dumps(comment(1006)) + "\n"
            fetched = fetch_issue_comments("ppow1/Riverview-", 120)
        args = run.call_args.args[0]
        self.assertEqual(args[:3], ["gh", "api", "--paginate"])
        self.assertEqual(fetched[0]["body"], comment(1006)["body"])
        self.assertTrue(run.call_args.kwargs["check"])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_watch_repeats_and_uses_capped_exponential_backoff(self):
        outcomes = [PollError("github_api_failed"), PollError("github_api_failed"),
                    PollError("github_api_failed"), {"ok": True}, {"ok": True}]
        delays = []
        reports = []
        def fake_poller(**_):
            value = outcomes.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        watch(state_path=self.state, interval_seconds=2, max_backoff_seconds=5,
              sleep=delays.append, poller=fake_poller, on_result=reports.append,
              max_cycles=5)
        self.assertEqual(delays, [2, 4, 5, 2])
        self.assertEqual(len(reports), 5)
        self.assertEqual(reports[0]["retry_in_seconds"], 2)


if __name__ == "__main__":
    unittest.main()

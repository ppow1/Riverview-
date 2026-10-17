# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_chatgpt_doorbell.py
# Component: CHATGPT-DOORBELL
# Revision: 1.0.1
# Purpose: Verify exact target binding, request identity, timeout bounds and metadata-only bridge results
# Execution Model: Deterministic unit tests; no browser, mailbox or network access
# Observability: unittest assertions and exit status
# Dependencies: Python standard library and riverview_core.doorbell
# Authority: Uses temporary config and fake process runner only
# Changed: 2026-10-17 UTC | RV-C3-DOORBELL-001 | Verify mismatched bridge lineage is rejected
# Contracts: docs/components/CHATGPT_DOORBELL.md
# Tests: This file
# History: Git and .riverview-revisions.json

from __future__ import annotations

import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from riverview_core.doorbell.browser_bridge import BrowserBridgeRunner, DoorbellRequest
from riverview_core.doorbell.config import bootstrap_config, load_config

CONVERSATION_ID = "6a804df2-a580-83ea-addc-753a6dc93f75"


class DoorbellTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.browser = self.root / "chrome"
        self.browser.write_text("test executable", encoding="utf-8")
        self.browser.chmod(0o700)
        self.config_path = self.root / "config" / "doorbell.json"
        bootstrap_config(CONVERSATION_ID, str(self.browser), self.config_path)
        self.request = DoorbellRequest(uuid4(), uuid4(), 60)

    def test_bootstrap_creates_private_exact_target_config(self):
        config = load_config(self.config_path)
        self.assertEqual(config.conversation_id, CONVERSATION_ID)
        self.assertEqual(config.browser_executable, self.browser.resolve())
        self.assertEqual(stat.S_IMODE(self.config_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.config_path.parent.stat().st_mode), 0o700)

    def test_bootstrap_preserves_existing_conversation_binding(self):
        with self.assertRaisesRegex(FileExistsError, "explicit replace"):
            bootstrap_config("11111111-1111-4111-8111-111111111111", str(self.browser), self.config_path)
        self.assertEqual(load_config(self.config_path).conversation_id, CONVERSATION_ID)

    def test_bootstrap_rejects_missing_browser_executable(self):
        with self.assertRaisesRegex(ValueError, "RIV-PLY-0013"):
            bootstrap_config(CONVERSATION_ID, str(self.root / "missing"), self.root / "other.json")

    def test_request_requires_uuid_identity_and_bounded_timeout(self):
        with self.assertRaisesRegex(ValueError, "RIV-PLY-0002"):
            DoorbellRequest(uuid4(), uuid4(), 121)
        with self.assertRaisesRegex(ValueError, "RIV-PLY-0002"):
            DoorbellRequest("not-a-uuid", uuid4())  # type: ignore[arg-type]

    def test_ring_preserves_request_correlation_and_returns_only_metadata(self):
        calls = []

        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, json.dumps({
                "status": "succeeded", "request_id": str(self.request.request_id),
                "correlation_id": str(self.request.correlation_id), "submit_verified": True,
                "evidence_ref": "riverview://doorbell/opaque",
                "designated_target_ref": "target-sha256:" + "a" * 64,
                "page_text": "must never pass through",
            }), "")

        result = BrowserBridgeRunner(
            bridge_path=self.root / "bridge.cjs", node_executable="node",
            config_path=self.config_path, runner=runner,
        ).ring(self.request, CONVERSATION_ID)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.request_id, self.request.request_id)
        self.assertEqual(result.correlation_id, self.request.correlation_id)
        self.assertEqual(result.evidence_ref, "riverview://doorbell/opaque")
        self.assertFalse(hasattr(result, "page_text"))
        payload = json.loads(calls[0][1]["input"])
        self.assertEqual(payload["request_id"], str(self.request.request_id))
        self.assertEqual(payload["correlation_id"], str(self.request.correlation_id))
        self.assertEqual(payload["operation"], "ring_riverview_doorbell")

    def test_ring_rejects_bridge_result_with_different_lineage(self):
        def mismatched(args, **_kwargs):
            return subprocess.CompletedProcess(args, 0, json.dumps({
                "status": "succeeded", "request_id": str(uuid4()),
                "correlation_id": str(self.request.correlation_id),
                "submit_verified": True,
            }), "")

        result = BrowserBridgeRunner(config_path=self.config_path, runner=mismatched).ring(
            self.request, CONVERSATION_ID)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_class, "RIV-PLY-0014")

    def test_ring_rejects_changed_designated_binding_before_launch(self):
        calls = []
        runner = lambda *args, **kwargs: calls.append((args, kwargs))
        adapter = BrowserBridgeRunner(config_path=self.config_path, runner=runner)
        with self.assertRaisesRegex(ValueError, "active Comms5 binding"):
            adapter.ring(self.request, "11111111-1111-4111-8111-111111111111")
        self.assertEqual(calls, [])

    def test_ring_converts_timeout_and_missing_node_to_bounded_failures(self):
        def timed_out(*_args, **_kwargs):
            raise subprocess.TimeoutExpired("node", 65)

        timeout_result = BrowserBridgeRunner(config_path=self.config_path, runner=timed_out).ring(
            self.request, CONVERSATION_ID)
        self.assertEqual(timeout_result.failure_class, "RIV-PLY-0009")

        def no_node(*_args, **_kwargs):
            raise FileNotFoundError("/usr/bin/node")

        missing_result = BrowserBridgeRunner(config_path=self.config_path, runner=no_node).ring(
            self.request, CONVERSATION_ID)
        self.assertEqual(missing_result.failure_class, "RIV-PLY-0015")


if __name__ == "__main__":
    unittest.main()

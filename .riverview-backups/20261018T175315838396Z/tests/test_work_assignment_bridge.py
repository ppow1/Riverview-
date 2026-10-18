# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_work_assignment_bridge.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-DISPATCH-BRIDGE-001 | Verify explicit alias events preserve unknown session state and v4 compatibility.
# Purpose: Test opt-in work-order receipt mirroring without polling or session control
# Authority: All fixtures are disposable; event receipts do not grant execution authorization
# Tests: This file
# =============================================================================
"""Tests for the request-driven v4 assignment receipt bridge."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

from riverview_core.work_registry import WorkRegistry
from scripts.record_work_assignment import capabilities, record_event


SOURCE = "https://github.com/ppow1/Riverview-/issues/120#issuecomment-6252352344"


class WorkAssignmentBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry_path = self.root / "registry.json"
        self.mapping_path = self.root / "mapping.json"
        self.status_path = self.root / "resource-routing.json"
        self.registry = WorkRegistry(self.registry_path)
        worker = self.registry.register_worker(worker_id="W1", worker_type="codex",
            hostname="fixture-host", os_name="Windows")
        self.registry.start_session("W1", session_id="W1", hostname="fixture-host",
            os_name="Windows", identity_state="unverified")
        document = json.loads(self.registry_path.read_text(encoding="utf-8"))
        session = document["sessions"]["W1"]
        session.update(lifecycle="unknown", activity_state="unknown", started_at=None,
                       last_heartbeat_at=None, last_activity_at=None)
        self.registry_path.write_text(json.dumps(document), encoding="utf-8")
        self.work = self.registry.create_work_order(work_order_id="work:issue120:round2:w1",
            worker_id="W1", owner_label="Windows W1 historical alias; identity unverified",
            title="W1 dispatch and monitoring bridge", status="queued",
            ownership_state="assigned", milestone=0, milestones_total=5,
            branch="feature/w1-control-board-state-accuracy",
            pull_request="https://github.com/ppow1/Riverview-/pull/127",
            evidence=[SOURCE])
        self.status_path.write_text(json.dumps({
            "task": "Previous W1 work", "status": "WAITING", "milestone": 4,
            "milestones_total": 4, "updated_at": "2026-10-18T12:00:00-04:00",
            "detail": "Historical status", "blocker": "", "next_action": "Review",
            "evidence": "Preserved historical evidence", "branch": "old-branch",
            "pr_url": "https://github.com/ppow1/Riverview-/pull/125",
        }), encoding="utf-8")
        self.mapping_path.write_text(json.dumps({
            "schema_version": "rv.work-registry.import-map.v1",
            "records": [{"worker_id": "W1", "session_id": "W1",
                "source": "resource-routing.json",
                "owner_label": "Windows W1 historical alias; identity unverified"}],
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def apply_event(self, event, **kwargs):
        return record_event(registry_path=self.registry_path, mapping_path=self.mapping_path,
            alias="W1", work_order_id=self.work["work_order_id"], event=event,
            source=SOURCE, **kwargs)

    def status(self):
        return json.loads(self.status_path.read_text(encoding="utf-8"))

    def test_ack_and_start_are_explicit_without_fabricating_session_lifecycle(self):
        original_keys = set(self.status())
        result = self.apply_event("acknowledged")
        self.assertTrue(result["recorded"])
        self.assertEqual(result["identity_state"], "unverified")
        self.assertEqual(result["session_lifecycle"], "unknown")
        self.assertEqual(result["session_activity"], "unknown")
        self.assertIsNone(result["last_heartbeat_at"])
        self.assertEqual(result["work_order_status"], "queued")
        self.assertEqual(self.status()["status"], "WAITING")
        self.assertEqual(self.status()["pr_url"], "https://github.com/ppow1/Riverview-/pull/127")
        self.assertEqual(set(self.status()), original_keys)
        self.assertEqual(self.status()["evidence"].count("Preserved historical evidence"), 1)

        result = self.apply_event("in_progress", milestone=1, milestones_total=5)
        snapshot = self.registry.snapshot()
        session = next(item for item in snapshot["sessions"] if item["session_id"] == "W1")
        order = next(item for item in snapshot["work_orders"] if item["work_order_id"] == self.work["work_order_id"])
        self.assertEqual(order["status"], "active")
        self.assertEqual(order["ownership_state"], "acknowledged")
        self.assertEqual(session["current_work_order_id"], order["work_order_id"])
        self.assertEqual(session["lifecycle"], "unknown")
        self.assertEqual(session["activity_state"], "unknown")
        self.assertIsNone(session["last_heartbeat_at"])
        self.assertEqual(self.status()["status"], "RUNNING")
        self.assertEqual(self.status()["milestone"], 1)
        self.assertEqual(self.status()["milestones_total"], 5)

    def test_blocked_and_completed_events_keep_the_session_observation_separate(self):
        self.apply_event("acknowledged")
        self.apply_event("in_progress")
        self.apply_event("blocked", blocker="Disposable fixture prerequisite")
        self.assertEqual(self.status()["status"], "BLOCKED")
        self.assertEqual(self.status()["blocker"], "Disposable fixture prerequisite")
        result = self.apply_event("completed", outcome="Fixture result verified")
        self.assertEqual(result["work_order_status"], "completed")
        self.assertEqual(result["session_lifecycle"], "unknown")
        self.assertEqual(result["session_activity"], "unknown")
        self.assertIsNone(result["last_heartbeat_at"])
        self.assertEqual(self.status()["status"], "COMPLETE")
        self.assertEqual(self.status()["blocker"], "")

    def test_concurrent_receipts_are_serialized_and_idempotent(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.apply_event("acknowledged"), range(4)))
        self.assertTrue(all(item["recorded"] for item in results))
        snapshot = self.registry.snapshot()
        order = next(item for item in snapshot["work_orders"] if item["work_order_id"] == self.work["work_order_id"])
        self.assertEqual(order["evidence"].count(
            f"assignment event=acknowledged; alias=W1; work_order_id={self.work['work_order_id']}; source={SOURCE}"), 1)
        self.assertEqual(self.status()["evidence"].count("assignment event=acknowledged"), 1)
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_remote_alias_requires_explicit_local_status_path(self):
        mapping = json.loads(self.mapping_path.read_text(encoding="utf-8"))
        mapping["records"][0]["source"] = "ssh://camrui/home/codex-1.json"
        self.mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "remote_alias_requires_explicit_local_status_path"):
            self.apply_event("acknowledged")

    def test_remote_alias_uses_only_an_explicit_local_status_override(self):
        mapping = json.loads(self.mapping_path.read_text(encoding="utf-8"))
        mapping["records"][0]["source"] = "ssh://camrui/home/codex-1.json"
        self.mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
        result = record_event(registry_path=self.registry_path, mapping_path=self.mapping_path,
            alias="W1", work_order_id=self.work["work_order_id"], event="acknowledged",
            source=SOURCE, status_json=self.status_path)
        self.assertTrue(result["recorded"])
        self.assertEqual(self.status()["status"], "WAITING")

    def test_capabilities_truthfully_report_no_poller_or_wake_transport(self):
        result = capabilities()
        self.assertFalse(result["automatic_github_polling"])
        self.assertFalse(result["existing_session_wake"])
        self.assertFalse(result["automatic_assignment_dispatch"])
        self.assertFalse(result["shared_windows_camrui_registry_verified"])


if __name__ == "__main__":
    unittest.main()

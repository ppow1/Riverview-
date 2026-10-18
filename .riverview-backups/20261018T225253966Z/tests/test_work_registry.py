# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_work_registry.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.2
# Purpose: Verify durable dynamic worker/session/work lifecycle and import safety
# Execution Model: Temporary file registry; concurrent writers; no services
# Observability: Assert persisted snapshots, explicit unknown/stale state, and privacy allowlist
# Authority: Registration and reporting provide no execution authorization
# Contracts: src/riverview_core/work_registry.py; docs/components/WORK_REGISTRY.schema.json
# =============================================================================
"""Focused cross-platform contract tests for the file-backed work registry."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import importlib.util
import tempfile
import unittest

from riverview_core.work_registry import SCHEMA_VERSION, WorkRegistry, WorkRegistryError


class WorkRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.registry = WorkRegistry(Path(self.temp.name) / "registry.json", stale_after_seconds=30)

    def register(self, worker_id="worker:one", **kwargs):
        return self.registry.register_worker(worker_id=worker_id, worker_type="codex",
            hostname="host-a", os_name="Windows", capabilities=["coding"], **kwargs)

    def test_dynamic_worker_and_session_discovery_has_no_fixed_session_count(self):
        for index in range(12):
            worker = self.registry.register_worker(worker_id=f"codex:{index}",
                worker_type="codex", hostname=f"host-{index}", os_name="Linux",
                capabilities=["engineering"])
            self.registry.start_session(worker["worker_id"], session_id=f"session:{index}")
        snapshot = self.registry.snapshot()
        self.assertEqual(len(snapshot["workers"]), 12)
        self.assertEqual(len(snapshot["sessions"]), 12)
        self.assertEqual(snapshot["schema_version"], SCHEMA_VERSION)

    def test_one_worker_has_concurrent_sessions_and_sequential_work_orders(self):
        self.register()
        first = self.registry.start_session("worker:one", session_id="session:first")
        second = self.registry.start_session("worker:one", session_id="session:second",
            os_name="Linux", hostname="camrui")
        self.assertNotEqual(first["session_id"], second["session_id"])
        a = self.registry.create_work_order(first["session_id"], title="First task", status="active")
        self.registry.update_work_order(a["work_order_id"], status="completed", outcome="Verified")
        b = self.registry.create_work_order(first["session_id"], title="Second task", status="active")
        snapshot = self.registry.snapshot()
        self.assertEqual(len(snapshot["sessions"]), 2)
        self.assertEqual(len(snapshot["work_orders"]), 2)
        self.assertEqual(next(x for x in snapshot["sessions"]
                              if x["session_id"] == first["session_id"])["current_work_order_id"],
                         b["work_order_id"])

    def test_concurrent_writers_preserve_every_registration_and_record(self):
        def write(index):
            worker_id = f"worker:{index}"
            session_id = f"session:{index}"
            self.registry.register_worker(worker_id=worker_id, worker_type="engineering",
                hostname="host", os_name="Linux", capabilities=["build"])
            self.registry.start_session(worker_id, session_id=session_id)
            return self.registry.create_work_order(session_id, title=f"Task {index}")["work_order_id"]
        with ThreadPoolExecutor(max_workers=12) as pool:
            work_ids = list(pool.map(write, range(36)))
        snapshot = self.registry.snapshot()
        self.assertEqual(len(snapshot["workers"]), 36)
        self.assertEqual(len(snapshot["sessions"]), 36)
        self.assertEqual(len(snapshot["work_orders"]), 36)
        self.assertEqual(len(set(work_ids)), 36)
        self.assertEqual(json.loads(self.registry.path.read_text(encoding="utf-8"))["schema_version"],
                         SCHEMA_VERSION)

    def test_unknown_stale_disconnected_and_completed_are_distinct(self):
        self.register()
        base = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        unknown = self.registry.start_session("worker:one", session_id="session:unknown",
            started_at=base)
        # A migrated session can retain unknown start/heartbeat rather than inventing one.
        document = json.loads(self.registry.path.read_text(encoding="utf-8"))
        document["sessions"][unknown["session_id"]].update(
            lifecycle="unknown", started_at=None, last_heartbeat_at=None)
        self.registry.path.write_text(json.dumps(document), encoding="utf-8")
        stale = self.registry.start_session("worker:one", session_id="session:stale",
            started_at=base - timedelta(minutes=2))
        disconnected = self.registry.start_session("worker:one", session_id="session:disconnected",
            started_at=base)
        completed = self.registry.start_session("worker:one", session_id="session:completed",
            started_at=base)
        self.registry.end_session(disconnected["session_id"], lifecycle="disconnected", at=base)
        self.registry.end_session(completed["session_id"], lifecycle="completed", at=base)
        rows = {item["session_id"]: item for item in self.registry.snapshot(now=base)["sessions"]}
        self.assertEqual(rows[unknown["session_id"]]["status"], "unknown")
        self.assertEqual(rows[stale["session_id"]]["status"], "stale")
        self.assertEqual(rows[disconnected["session_id"]]["status"], "disconnected")
        self.assertEqual(rows[completed["session_id"]]["status"], "completed")
        self.assertIn(completed["session_id"], rows)  # historical session retained

    def test_heartbeat_age_does_not_create_ai_reasoning_activity(self):
        self.register()
        session = self.registry.start_session("worker:one", session_id="session:ai",
            model_identity="Qwen-80B")
        self.registry.heartbeat(session["session_id"], activity_state="unknown")
        observed = self.registry.snapshot()["sessions"][0]
        self.assertEqual(observed["activity_state"], "unknown")
        self.assertIn("do not prove model reasoning", self.registry.snapshot()["activity_semantics"])

    def test_local_ai_job_has_dynamic_slot_and_safe_endpoint_reference(self):
        self.registry.register_worker(worker_id="local-ai:qwen", worker_type="local_ai",
            hostname="gpu-host", os_name="Linux", capabilities=["inference"],
            model_identity="Qwen3-Next-80B", endpoint_ref="inference-host-primary")
        session = self.registry.start_session("local-ai:qwen", session_id="service:inference",
            model_identity="Qwen3-Next-80B", endpoint_ref="inference-host-primary")
        job = self.registry.create_work_order(session["session_id"], title="Inference job",
            status="queued", local_ai_job={"model_identity":"Qwen3-Next-80B",
                "endpoint_ref":"inference-host-primary", "slot":"gpu-slot-8",
                "queue_status":"queued", "task_correlation_id":"task:123",
                "started_at":None, "completed_at":None})
        self.assertEqual(job["local_ai_job"]["slot"], "gpu-slot-8")
        self.assertIsNone(job["local_ai_job"]["started_at"])

    def test_registry_rejects_prompts_credentials_and_unversioned_import_fields(self):
        self.register()
        session = self.registry.start_session("worker:one")
        with self.assertRaisesRegex(ValueError, "unsupported work-order update"):
            self.registry.update_work_order("missing", prompt="never store prompts")
        with self.assertRaisesRegex(ValueError, "sensitive content"):
            self.registry.create_work_order(session["session_id"], title="Safe title",
                detail="System prompt: private instructions")
        with self.assertRaisesRegex(ValueError, "sensitive content"):
            self.registry.register_worker(worker_id="worker:secret", worker_type="local_ai",
                hostname="host", os_name="Linux", endpoint_ref="https://host/?api_key=secret")
        source = self.registry._read_unlocked()
        source["sessions"][session["session_id"]]["reasoning_trace"] = "private"
        with self.assertRaises(ValueError):
            self.registry.import_document(source)

    def test_import_is_additive_and_conflicts_fail_without_overwriting_existing(self):
        imported = WorkRegistry(Path(self.temp.name) / "import.json")
        imported.register_worker(worker_id="worker:imported", worker_type="codex",
            hostname="windows", os_name="Windows", capabilities=[])
        imported.start_session("worker:imported", session_id="session:imported")
        self.registry.import_document(imported._read_unlocked())
        self.register()
        snapshot = self.registry.import_document(imported._read_unlocked())
        self.assertEqual(len(snapshot["workers"]), 2)
        conflict = imported._read_unlocked()
        conflict["workers"]["worker:imported"]["hostname"] = "other-host"
        with self.assertRaises(WorkRegistryError):
            self.registry.import_document(conflict)
        self.assertEqual(self.registry.snapshot()["workers"][0]["hostname"], "windows")

    def test_work_order_can_precede_observed_worker_and_session(self):
        item = self.registry.create_work_order(title="Proposed work", status="unknown",
            owner_label="Windows W2 proposed follow-up", ownership_state="proposed",
            evidence=["https://github.com/ppow1/Riverview-/issues/120"])
        self.assertIsNone(item["session_id"])
        self.assertIsNone(item["worker_id"])
        self.assertEqual(item["ownership_state"], "proposed")
        self.assertEqual(len(self.registry.snapshot()["sessions"]), 0)

    def test_session_startup_acknowledges_assignment_without_inventing_activity(self):
        item = self.registry.create_work_order(title="Issue inventory task", status="queued",
            owner_label="Windows W1", ownership_state="proposed")
        self.register()
        session = self.registry.start_session("worker:one", session_id="session:received")
        observed = self.registry.acknowledge_work_order(item["work_order_id"],
            "worker:one", session["session_id"])
        snapshot = self.registry.snapshot()
        self.assertEqual(observed["ownership_state"], "acknowledged")
        self.assertEqual(observed["worker_id"], "worker:one")
        self.assertEqual(observed["session_id"], "session:received")
        self.assertEqual(snapshot["sessions"][0]["activity_state"], "unknown")
        self.assertEqual(snapshot["sessions"][0]["last_activity_at"], None)

    def test_issue_120_import_is_idempotent_and_never_synthesizes_sessions(self):
        script = Path(__file__).parents[1] / "scripts/import_issue_120_work_inventory.py"
        spec = importlib.util.spec_from_file_location("issue120_import", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = Path(__file__).parents[1] / "docs/operations/ISSUE_120_INITIAL_WORK_INVENTORY.json"
        dry = module.import_inventory(source, self.registry.path, dry_run=True)
        self.assertEqual(dry["items_added"], 12)
        self.assertFalse(self.registry.path.exists())
        result = module.import_inventory(source, self.registry.path)
        self.assertEqual(result["items_added"], 12)
        again = module.import_inventory(source, self.registry.path)
        self.assertEqual(again["items_added"], 0)
        snapshot = self.registry.snapshot()
        self.assertEqual(len(snapshot["workers"]), 0)
        self.assertEqual(len(snapshot["sessions"]), 0)
        self.assertEqual(len(snapshot["work_orders"]), 12)
        c4 = next(item for item in snapshot["work_orders"] if item["owner_label"] == "Camrui C4")
        self.assertEqual((c4["milestone"], c4["milestones_total"]), (1, 5))
        from jsonschema import Draft202012Validator
        schema = json.loads((Path(__file__).parents[1] /
            "docs/components/WORK_REGISTRY.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(self.registry._read_unlocked()))
        self.assertEqual(errors, [])

    def test_legacy_import_requires_explicit_ids_and_does_not_infer_activity_from_file_update(self):
        script = Path(__file__).parents[1] / "scripts/import_work_registry.py"
        spec = importlib.util.spec_from_file_location("legacy_import", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = Path(self.temp.name) / "legacy.json"
        source.write_text(json.dumps({"status":"RUNNING", "task":"Observed task",
                                      "updated_at":"2026-10-18T10:00:00-04:00"}), encoding="utf-8")
        mapping = Path(self.temp.name) / "mapping.json"
        mapping.write_text(json.dumps({"schema_version":"rv.work-registry.import-map.v1",
            "records":[{"source":str(source), "worker_id":"worker:legacy",
                "session_id":"session:legacy", "hostname":"old-host", "os":"Windows"}]}),
            encoding="utf-8")
        before = source.read_bytes()
        result = module.import_map(mapping, self.registry.path)
        self.assertEqual(result["sessions_added"], 1)
        self.assertEqual(source.read_bytes(), before)
        session = self.registry.snapshot()["sessions"][0]
        self.assertEqual(session["lifecycle"], "unknown")
        self.assertIsNone(session["last_heartbeat_at"])
        self.assertIsNone(session["last_activity_at"])
        self.assertEqual(session["started_at"], None)

    def test_v4_import_keeps_legacy_alias_explicitly_unverified_and_preserves_assignment_only(self):
        script = Path(__file__).parents[1] / "scripts/import_work_registry.py"
        spec = importlib.util.spec_from_file_location("legacy_import_unverified", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = Path(self.temp.name) / "v4.json"
        source.write_text(json.dumps({"task":"Previous assignment", "status":"COMPLETE",
            "updated_at":"2026-10-18T10:00:00-04:00", "milestone":2,
            "milestones_total":2,
            "evidence":["PR delivered", "legacy v4 source: w1.json"]}), encoding="utf-8")
        mapping = Path(self.temp.name) / "mapping-unverified.json"
        mapping.write_text(json.dumps({"schema_version":"rv.work-registry.import-map.v1",
            "records":[{"source":str(source), "worker_id":"W1", "session_id":"W1",
                "hostname":"windows-host", "os":"Windows", "lifecycle":"unknown",
                "identity_state":"unverified", "assignment_title":"Previous assignment",
                "owner_label":"W1 legacy alias; session identity UNVERIFIED",
                "ownership_state":"assigned", "source_evidence":"legacy v4 source: w1.json"}]}),
            encoding="utf-8")
        module.import_map(mapping, self.registry.path)
        snapshot = self.registry.snapshot()
        session = snapshot["sessions"][0]
        work = snapshot["work_orders"][0]
        self.assertEqual(session["session_id"], "W1")
        self.assertEqual(session["identity_state"], "unverified")
        self.assertEqual(session["status"], "unknown")
        self.assertEqual(session["activity_state"], "unknown")
        self.assertIsNone(session["last_heartbeat_at"])
        self.assertIsNone(session["last_activity_at"])
        self.assertEqual(work["status"], "completed")
        self.assertIsNone(work["completed_at"])
        self.assertIn("legacy v4 source: w1.json", work["evidence"])

        source.write_text(json.dumps({"task":"Previous assignment", "status":"RUNNING",
            "updated_at":"2026-10-18T11:00:00-04:00", "milestone":3,
            "milestones_total":3}), encoding="utf-8")
        refreshed = module.import_map(mapping, self.registry.path)
        self.assertEqual(refreshed["work_orders_updated"], 1)
        session = next(item for item in self.registry.snapshot()["sessions"]
                       if item["session_id"] == "W1")
        self.assertEqual(session["identity_state"], "unverified")
        self.assertIsNone(session["last_heartbeat_at"])
        work = next(item for item in self.registry.snapshot()["work_orders"]
                    if item["session_id"] == "W1")
        self.assertEqual(work["status"], "active")
        self.assertIsNone(work["started_at"])
        self.assertIsNone(work["completed_at"])
        self.assertTrue(any("completed -> active" in item for item in work["evidence"]))

        source.write_text(json.dumps({"task":"Previous assignment", "status":"RUNNING",
            "updated_at":"2026-10-18T11:00:00.9516467-04:00", "milestone":3,
            "milestones_total":3}), encoding="utf-8")
        same_second = module.import_map(mapping, self.registry.path)
        self.assertEqual(same_second["work_orders_updated"], 0)

        mapping_doc = json.loads(mapping.read_text(encoding="utf-8"))
        mapping_doc["records"][0]["assignment_title"] = "Later assignment"
        mapping.write_text(json.dumps(mapping_doc), encoding="utf-8")
        source.write_text(json.dumps({"status":"RUNNING",
            "updated_at":"2026-10-18T12:00:00-04:00"}), encoding="utf-8")
        added = module.import_map(mapping, self.registry.path)
        self.assertEqual(added["work_orders_added"], 1)
        orders = [item for item in self.registry.snapshot()["work_orders"]
                  if item["session_id"] == "W1"]
        self.assertEqual({item["title"] for item in orders},
                         {"Previous assignment", "Later assignment"})
        self.assertEqual(module.import_map(mapping, self.registry.path)["work_orders_updated"], 0)

    def test_previous_v1_session_without_identity_state_remains_compatible(self):
        self.register()
        self.registry.start_session("worker:one", session_id="session:old")
        old = self.registry._read_unlocked()
        old["sessions"]["session:old"].pop("identity_state")
        migrated = WorkRegistry(Path(self.temp.name) / "old-snapshot.json")
        migrated.import_document(old)
        self.assertEqual(migrated.snapshot()["sessions"][0]["identity_state"], "verified")


if __name__ == "__main__":
    unittest.main()

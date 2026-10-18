# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_work_registry_dashboard.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Purpose: Verify authenticated registry snapshot route and dynamic UI wiring
# Execution Model: Loopback dashboard HTTP test with temporary file registry
# Authority: Registry API is read-only; no service or inference host is started
# Tests: This file
# =============================================================================
"""Focused HTTP and dashboard contract tests for the universal registry."""
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from riverview_core.status_dashboard.server import DashboardHTTPServer
from riverview_core.work_registry import WorkRegistry


ROOT = Path(__file__).resolve().parents[1]


class WorkRegistryDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        registry = WorkRegistry(Path(self.temp.name) / "registry.json")
        worker = registry.register_worker(worker_id="worker:dynamic", worker_type="local_ai",
            hostname="inference-host", os_name="Linux", capabilities=["vision"],
            model_identity="local-vlm")
        session = registry.start_session(worker["worker_id"], session_id="session:dynamic",
            repository="repo", branch="feature/dynamic")
        registry.create_work_order(session["session_id"], title="Vision job", status="active",
            detail="Safe summary", local_ai_job={"model_identity":"local-vlm",
                "endpoint_ref":"inference-host", "slot":"slot-9", "queue_status":"running",
                "task_correlation_id":"task:9", "started_at":None, "completed_at":None})
        self.registry = registry
        self.token = "registry-dashboard-test-token"
        self.server = None
        for port in range(8799, 8699, -1):
            try:
                with patch("riverview_core.status_dashboard.server._read_token", return_value=self.token):
                    self.server = DashboardHTTPServer("127.0.0.1", port, "unused",
                        projection=object(), static_dir=ROOT / "src/riverview_core/status_dashboard/static",
                        work_registry=registry)
                break
            except OSError:
                continue
        if self.server is None:
            self.fail("no reserved loopback test port was available")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close_server(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)
            self.server = None

    def test_snapshot_is_authenticated_and_enumerates_dynamic_records(self):
        with self.assertRaises(HTTPError) as denied:
            urlopen(self.base + "/api/v1/work-registry", timeout=3)
        self.assertEqual(denied.exception.code, 401)
        req = Request(self.base + "/api/v1/work-registry",
                      headers={"Authorization": f"Bearer {self.token}"})
        with urlopen(req, timeout=3) as response:
            import json
            payload = json.loads(response.read())
        self.assertEqual(len(payload["workers"]), 1)
        self.assertEqual(len(payload["sessions"]), 1)
        self.assertEqual(payload["work_orders"][0]["local_ai_job"]["slot"], "slot-9")
        self.assertEqual(payload["sessions"][0]["activity_state"], "unknown")

    def test_registration_is_not_exposed_as_dashboard_write_and_view_is_dynamic(self):
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        js = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        server = (ROOT / "src/riverview_core/status_dashboard/server.py").read_text(encoding="utf-8")
        self.assertIn('id="view-work-registry"', html)
        self.assertIn('api("/api/v1/work-registry")', js)
        self.assertIn("orders.length", js)
        self.assertIn("sessionRows.concat(idle, workRows)", js)
        self.assertIn("heartbeat_age_seconds", js)
        self.assertIn('parsed.path == "/api/v1/work-registry"', server)
        self.assertIn('self.command not in {"GET", "HEAD"}', server)

    def test_unconfigured_registry_and_legacy_worker_projection_remain_available(self):
        import json
        self.server._work_registry = None
        req = Request(self.base + "/api/v1/work-registry",
                      headers={"Authorization": f"Bearer {self.token}"})
        with urlopen(req, timeout=3) as response:
            self.assertEqual(json.loads(response.read())["status"], "not_initialized")

        class LegacyProjection:
            def workers(self, *, after=None, limit=25):
                return {"status":"available", "items":[{"worker_id":"legacy-worker"}],
                        "next_cursor":None}

        self.server._projection = LegacyProjection()
        req = Request(self.base + "/api/v1/workers?limit=25",
                      headers={"Authorization": f"Bearer {self.token}"})
        with urlopen(req, timeout=3) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["items"][0]["worker_id"], "legacy-worker")


if __name__ == "__main__":
    unittest.main()

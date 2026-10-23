# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_comfyui_adapter.py
# Component: ENGINEERING-COMFYUI-ADAPTER
# Revision: 1.0.2
# Changed: 2026-10-23 UTC | RIVERVIEW-COMFYUI-REGISTRY-PERMISSION | Assert worker registry config uses a root-readable immutable release path.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Exercise canonical colon-delimited assignment IDs used by Grace.
# Purpose: Mock ComfyUI transport, durable execution, recovery, artifact and verifier contracts
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Mock-server acceptance for the bounded ComfyUI Engineering action."""
import hashlib
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from riverview_core.worker_adapter.comfyui import (
    CAPABILITY, ComfyUIAction, ComfyUIError, ComfyUIOutputVerifier,
    ComfyUIKnowledgeProvider, ComfyUITemplateError, ComfyUIWorkflowRegistry,
)
from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider

# Valid signature/header bytes are enough for the adapter's content-type and hash
# boundary; GPU execution is deliberately not represented by this mock fixture.
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg==")


class MockComfy:
    def __init__(self):
        self.posts = 0
        self.views = 0
        self.template_sha256 = None
        self.assignment_id = None
        self.fail_view_number = None
        self.lose_post_response = False
        self.fail_history_once = False
        self.never_complete = False
        self.lock = threading.Lock()
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                if self.path == "/prompt":
                    with owner.lock:
                        owner.posts += 1
                        owner.template_sha256 = body.get("extra_data", {}).get("riverview_template_sha256")
                        owner.assignment_id = body.get("extra_data", {}).get("riverview_assignment")
                    if owner.lose_post_response:
                        self.connection.shutdown(1)
                        self.connection.close()
                        return
                    if body.get("prompt", {}).get("3", {}).get("inputs", {}).get("steps") != 12:
                        self.send_error(422); return
                    self._json({"prompt_id": "12345678-1234-1234-1234-123456789abc"})
                elif self.path == "/queue":
                    self._json({"deleted": body.get("delete", [])})
                else:
                    self.send_error(404)
            def do_GET(self):
                if self.path.startswith("/history/"):
                    if owner.fail_history_once:
                        owner.fail_history_once = False
                        self.send_error(503); return
                    if owner.never_complete:
                        self._json({})
                    else:
                        self._json({"12345678-1234-1234-1234-123456789abc": {
                            "status": {"status_str": "success"},
                            "prompt": [1, {}, {"riverview_assignment": owner.assignment_id,
                                "riverview_template_sha256": owner.template_sha256}, []],
                            "outputs": {"2": {"images": [
                                {"filename": "one.png", "subfolder": "", "type": "output"},
                                {"filename": "two.png", "subfolder": "", "type": "output"}]}}}})
                elif self.path.startswith("/view?"):
                    with owner.lock:
                        owner.views += 1
                        view_no = owner.views
                    if owner.fail_view_number == view_no:
                        self.send_error(503); return
                    self.send_response(200); self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(PNG))); self.end_headers(); self.wfile.write(PNG)
                elif self.path == "/queue":
                    self._json({"queue_running": [], "queue_pending": []})
                else:
                    self.send_error(404)
            def _json(self, value):
                raw = json.dumps(value).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"
    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)


def registry():
    return ComfyUIWorkflowRegistry({"test-txt2img": {
        "revision": "fixture-1", "workflow": {
            "3": {"class_type": "KSampler", "inputs": {"steps": 8}},
            "2": {"class_type": "SaveImage", "inputs": {"filename_prefix": "test"}},
        }, "bindings": {"steps": {"node": "3", "input": "steps", "type": "integer", "min": 1, "max": 30}},
        "output_nodes": ["2"]}})


class ComfyUIAdapterTests(unittest.TestCase):
    def test_worker_registry_configuration_uses_readable_release_path(self):
        dropin = Path(__file__).parents[1] / "deploy/systemd/riverview-grace-comfyui.conf"
        config = dropin.read_text(encoding="utf-8")
        self.assertIn(
            "RIVERVIEW_COMFYUI_WORKFLOW_REGISTRY=/opt/riverview-grace-execution/current/deploy/comfyui/workflows.json",
            config,
        )
        self.assertNotIn("RIVERVIEW_COMFYUI_WORKFLOW_REGISTRY=/etc/riverview/", config)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.artifacts = root / "artifacts"; self.artifacts.mkdir(mode=0o700)
        self.state = root / "state"; self.state.mkdir(mode=0o700)
        self.mock = MockComfy()
        self.assignment = {"id": "assignment:grace:0000000000000000000000000000000000000001"}
        self.grounded = SimpleNamespace(value={"workflow_id": "test-txt2img", "parameters": {"steps": 12}})
        self.action = self.make_action()
    def tearDown(self):
        self.mock.close(); self.temp.cleanup()
    def make_action(self, **kwargs):
        return ComfyUIAction(self.mock.endpoint, registry(), self.artifacts, self.state,
            timeout_seconds=kwargs.get("timeout_seconds", 5), poll_interval=kwargs.get("poll_interval", 0.1),
            request_timeout_seconds=kwargs.get("request_timeout_seconds", 0.5))

    def test_success_submits_registered_workflow_and_verifier_reopens_image(self):
        result = self.action(self.assignment, self.grounded)
        self.assertEqual(self.mock.posts, 1)
        self.assertEqual(result["artifact_schema"], "rv.engineering.comfyui-artifacts.v1")
        self.assertEqual(len(result["artifacts"]), 2)
        self.assertEqual(result["artifacts"][0]["sha256"], hashlib.sha256(PNG).hexdigest())
        result_sha = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        verified = ComfyUIOutputVerifier(self.artifacts).verify(self.assignment,
            {"status": "succeeded", "capability": CAPABILITY, "attempt_id": "attempt-1", "result_sha256": result_sha}, result)
        self.assertEqual(verified.status.value, "ACCEPTED")
        artifact = self.artifacts / result["artifacts"][0]["storage_name"]
        artifact.write_bytes(b"tampered")
        rejected = ComfyUIOutputVerifier(self.artifacts).verify(self.assignment,
            {"status": "succeeded", "capability": CAPABILITY, "attempt_id": "attempt-1", "result_sha256": result_sha}, result)
        self.assertEqual(rejected.status.value, "REJECTED")

    def test_capability_is_registered_under_existing_exact_execute_boundary(self):
        from riverview_core.worker_adapter.adapter import PostgresWorkerAdapter
        self.assertEqual(PostgresWorkerAdapter.COMFYUI_CAPABILITY, CAPABILITY)
        self.assertEqual(RepositoryKnowledgeProvider.ACTIONS[CAPABILITY],
                         RepositoryKnowledgeProvider.WORKER_CONTRACT)

    def test_invalid_workflow_and_parameters_are_rejected_before_submission(self):
        with self.assertRaises(ComfyUITemplateError):
            self.action(self.assignment, SimpleNamespace(value={"workflow_id": "unregistered", "parameters": {}}))
        with self.assertRaises(ComfyUITemplateError):
            self.action(self.assignment, SimpleNamespace(value={"workflow_id": "test-txt2img", "parameters": {"steps": 99}}))
        self.assertEqual(self.mock.posts, 0)

    def test_timeout_is_bounded_and_recorded(self):
        self.mock.never_complete = True
        action = self.make_action(timeout_seconds=5)
        with self.assertRaisesRegex(ComfyUIError, "execution_timeout"):
            action(self.assignment, self.grounded)
        self.assertEqual(self.mock.posts, 1)
        # Resuming the same assignment reuses its known prompt instead of posting twice.
        self.mock.never_complete = False
        result = action(self.assignment, self.grounded)
        self.assertEqual(len(result["artifacts"]), 2)
        self.assertEqual(self.mock.posts, 1)

    def test_duplicate_submission_returns_journaled_result(self):
        first = self.action(self.assignment, self.grounded)
        second = self.action(self.assignment, self.grounded)
        self.assertEqual(first, second)
        self.assertEqual(self.mock.posts, 1)

    def test_progress_callback_reports_bounded_job_state(self):
        updates = []
        action = ComfyUIAction(self.mock.endpoint, registry(), self.artifacts, self.state,
            timeout_seconds=5, poll_interval=0.1, request_timeout_seconds=0.5,
            progress_callback=updates.append)
        action(self.assignment, self.grounded)
        self.assertTrue(any(item["status"] == "running" for item in updates))
        self.assertEqual(updates[-1]["status"], "complete")
        self.assertEqual(updates[-1]["outputs_saved"], 2)
        self.assertNotIn("parameters", updates[-1])

    def test_lost_submission_response_is_indeterminate_and_never_replayed(self):
        self.mock.lose_post_response = True
        for _ in range(2):
            with self.assertRaises(ComfyUIError):
                self.action(self.assignment, self.grounded)
        self.assertEqual(self.mock.posts, 1)

    def test_lost_connection_after_prompt_id_recovers_without_resubmission(self):
        self.mock.fail_history_once = True
        with self.assertRaises(ComfyUIError):
            self.action(self.assignment, self.grounded)
        result = self.action(self.assignment, self.grounded)
        self.assertEqual(len(result["artifacts"]), 2)
        self.assertEqual(self.mock.posts, 1)

    def test_partial_output_is_recovered_without_resubmission(self):
        self.mock.fail_view_number = 2
        with self.assertRaises(ComfyUIError):
            self.action(self.assignment, self.grounded)
        self.assertEqual(len([path for path in self.artifacts.rglob("*") if path.is_file()]), 1)
        self.mock.fail_view_number = None
        result = self.action(self.assignment, self.grounded)
        self.assertEqual(len(result["artifacts"]), 2)
        self.assertEqual(self.mock.posts, 1)

    def test_cancel_only_targets_persisted_prompt(self):
        self.mock.never_complete = True
        # With a 5s budget, start an action in the background and wait for its prompt journal.
        thread = threading.Thread(target=lambda: self._ignore_action_error(), daemon=True)
        thread.start()
        for _ in range(50):
            files = list(self.state.glob("*.json"))
            if files:
                try:
                    if json.loads(files[0].read_text()).get("prompt_id"):
                        break
                except (OSError, ValueError):
                    pass
            threading.Event().wait(0.02)
        self.assertTrue(self.action.cancel(self.assignment["id"]))
        thread.join(timeout=6)

    def test_verified_work_order_grounding_supplies_only_structured_request(self):
        class Provider:
            def ground_assignment(self, _):
                return KnowledgeResult(KnowledgeStatus.VERIFIED, value={"docs": []},
                    source_references=("repo://worker-contract",), source_revision="a" * 40,
                    source_sha256="b" * 64, retrieval_complete=True)
            def preflight_action(self, *_): return self.ground_assignment(None)
            def reground_assignment(self, *_): return self.ground_assignment(None)
            def record_learning(self, *_): return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
        wrapper = ComfyUIKnowledgeProvider(Provider(), lambda _: {
            "workflow_id": "test-txt2img", "parameters": {"steps": 12}})
        result = wrapper.ground_assignment(self.assignment)
        self.assertEqual(result.status, KnowledgeStatus.VERIFIED)
        self.assertEqual(result.value, {"workflow_id": "test-txt2img", "parameters": {"steps": 12}})

    def _ignore_action_error(self):
        try: self.action(self.assignment, self.grounded)
        except ComfyUIError: pass


if __name__ == "__main__":
    unittest.main()

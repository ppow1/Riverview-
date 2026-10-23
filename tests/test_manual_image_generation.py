# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_manual_image_generation.py
# Component: V2-MANUAL-IMAGE-GENERATION
# Revision: 1.0.6
# Purpose: Verify durable operator mode through the registered ComfyUI action
# =============================================================================
# Changed: 2026-10-23 UTC | RV-ISSUE-250 | Use actual history tuple and cover valid, mismatched and stale identities.
# Changed: 2026-10-23 UTC | RV-ISSUE-256 | Verify both SD-Turbo and dynamic RealVisXL catalog registrations.
"""Mock ComfyUI execution and independent artifact acceptance for manual mode."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.parse import urlsplit

from riverview_core.status_dashboard.manual_image_generation import (
    ManualImageError, ManualImageGenerationService,
)

ROOT = Path(__file__).resolve().parents[1]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg==")
PROMPT_ID = "12345678-1234-1234-1234-123456789abc"


class ManualMockComfy:
    def __init__(self):
        self.posts = 0
        self.assignment = None
        self.template_digest = None
        self.fail_worker = False
        self.fail_execution = False
        self.history_assignment_override = None
        self.history_prompt_id_override = None
        self.views = 0
        self.devices = [{"name": "Test GPU", "vram_total": 8_000_000_000,
                         "vram_free": 7_000_000_000}]
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def _json(self, value, status=200):
                body = json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path != "/prompt":
                    self.send_error(404); return
                with owner.lock:
                    owner.posts += 1
                    owner.assignment = data.get("extra_data", {}).get("riverview_assignment")
                    owner.template_digest = data.get("extra_data", {}).get("riverview_template_sha256")
                self._json({"prompt_id": PROMPT_ID})

            def do_GET(self):
                if self.path == "/system_stats":
                    if owner.fail_worker:
                        self.send_error(503); return
                    self._json({"devices": owner.devices})
                elif self.path == "/queue":
                    self._json({"queue_running": [], "queue_pending": []})
                elif self.path.startswith("/history/"):
                    prompt_id = owner.history_prompt_id_override or PROMPT_ID
                    assignment = owner.history_assignment_override or owner.assignment
                    self._json({PROMPT_ID: {"status": {"status_str": "error" if owner.fail_execution else "success"},
                        "prompt": [1, prompt_id, {}, {"riverview_assignment": assignment,
                            "riverview_template_sha256": owner.template_digest}, []],
                        "outputs": {"9": {"images": [{"filename": "manual.png",
                            "subfolder": "", "type": "output"}]}}}})
                elif self.path.startswith("/view?"):
                    owner.views += 1
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(PNG)))
                    self.end_headers()
                    self.wfile.write(PNG)
                else:
                    self.send_error(404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)


class ManualImageGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.artifacts = root / "artifacts"
        self.state = root / "state"
        self.mock = ManualMockComfy()
        self.service = ManualImageGenerationService(
            endpoint=self.mock.endpoint,
            registry_path=ROOT / "deploy/comfyui/workflows.json",
            artifact_root=self.artifacts, state_root=self.state,
            timeout_seconds=5, poll_interval=0.1, output_host="test-controller")

    def tearDown(self):
        self.mock.close()
        self.temp.cleanup()

    def submit(self, **overrides):
        values = {"request_id": "8b0e3be5-c68c-41e3-9a4e-e659c291f703",
            "actor_id": "account-operator-1", "actor_role": "operator",
            "workflow_id": "sd-turbo-text-to-image.v1",
            "parameters": {"prompt": "A small red cube on a plain white background", "seed": 7}}
        values.update(overrides)
        return self.service.submit(**values)

    def wait(self, request_id="8b0e3be5-c68c-41e3-9a4e-e659c291f703"):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            record = self.service.get(request_id)
            if record and record["status"] in {"complete", "failed"}:
                return record
            time.sleep(0.01)
        self.fail("manual image execution did not finish")

    def test_registered_workflow_completes_verified_artifact_and_download_bytes(self):
        catalog = self.service.catalog()
        self.assertEqual({row["workflow_id"] for row in catalog["workflows"]},
                         {"realvisxl-v5-photorealistic.v1", "sd-turbo-text-to-image.v1"})
        turbo = next(row for row in catalog["workflows"]
                     if row["workflow_id"] == "sd-turbo-text-to-image.v1")
        photoreal = next(row for row in catalog["workflows"]
                         if row["workflow_id"] == "realvisxl-v5-photorealistic.v1")
        self.assertEqual(turbo["fixed_resolution"],
                         {"width": 512, "height": 512})
        self.assertEqual({item["name"]: item.get("default") for item in turbo["parameters"]},
                         {"prompt": None, "seed": 7})
        self.assertEqual(photoreal["fixed_resolution"], {"width": 1024, "height": 1024})
        self.assertEqual({item["name"]: item.get("default") for item in photoreal["parameters"]},
                         {"prompt": None, "seed": 7})
        self.assertFalse(catalog["gpu_selection_supported"])
        self.assertEqual(catalog["worker"]["device"]["name"], "Test GPU")
        self.submit()
        record = self.wait()
        self.assertEqual(record["status"], "complete")
        self.assertEqual(record["execution_kind"], "operator_manual")
        self.assertIsNone(record["work_order_id"])
        self.assertIsNone(record["engineering_assignment_id"])
        self.assertEqual(record["verification"]["decision"], "ACCEPTED")
        self.assertEqual(record["artifact"]["host"], "test-controller")
        self.assertEqual(record["worker"]["device"]["name"], "Test GPU")
        self.assertEqual(record["artifact"]["device"]["name"], "Test GPU")
        self.assertEqual(Path(record["artifact"]["absolute_path"]).read_bytes(), PNG)
        metadata, downloaded = self.service.image_bytes(record["request_id"])
        self.assertEqual(metadata["artifact"]["sha256"], hashlib.sha256(downloaded).hexdigest())
        self.assertEqual(downloaded, PNG)
        self.assertEqual(self.mock.posts, 1)

    def test_photoreal_workflow_is_registered_and_keeps_turbo_checkpoint_independent(self):
        registry = self.service.registry
        graph, template, _ = registry.render("realvisxl-v5-photorealistic.v1", {
            "prompt": "A dog walking along a sidewalk, candid DSLR photograph, realistic fur, natural lighting, photographic detail, not a painting or illustration.",
            "seed": 7,
        })
        self.assertEqual(template["revision"], "realvisxl-v5-fp16-1024-30step-v1")
        self.assertEqual(graph["4"]["inputs"]["ckpt_name"], "RealVisXL_V5.0_fp16.safetensors")
        self.assertEqual(graph["5"]["inputs"], {"width": 1024, "height": 1024, "batch_size": 1})
        self.assertEqual(graph["3"]["inputs"]["steps"], 30)
        self.assertEqual(graph["3"]["inputs"]["sampler_name"], "dpmpp_2m")
        self.assertEqual(graph["3"]["inputs"]["scheduler"], "karras")
        self.assertIn("painting", graph["7"]["inputs"]["text"])
        turbo_graph, _, _ = registry.render("sd-turbo-text-to-image.v1", {"prompt": "same scene", "seed": 7})
        self.assertEqual(turbo_graph["4"]["inputs"]["ckpt_name"], "sd_turbo.safetensors")
        self.assertEqual(turbo_graph["5"]["inputs"]["width"], 512)


    def test_history_rejects_cross_assignment_identity_without_retrieving_image(self):
        self.mock.history_assignment_override = "manual:another-request"
        self.submit()
        record = self.wait()
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "history_identity_mismatch")
        self.assertIsNone(record["artifact"])
        self.assertEqual(self.mock.views, 0)

    def test_stale_history_entry_is_not_treated_as_the_submitted_prompt(self):
        self.mock.history_prompt_id_override = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        self.submit()
        record = self.wait()
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "history_identity_mismatch")
        self.assertIsNone(record["artifact"])
        self.assertEqual(self.mock.views, 0)

    def test_duplicate_request_id_is_idempotent_and_changed_request_conflicts(self):
        first = self.submit()
        second = self.submit()
        self.assertEqual(first["request_id"], second["request_id"])
        with self.assertRaises(ManualImageError) as caught:
            self.submit(parameters={"prompt": "different", "seed": 7})
        self.assertEqual(caught.exception.status, 409)
        self.wait()
        self.assertEqual(self.mock.posts, 1)

    def test_invalid_workflow_parameters_fail_before_comfy_submission(self):
        with self.assertRaises(ManualImageError):
            self.submit(parameters={"prompt": "test", "seed": 7, "gpu_uuid": "unapproved"})
        with self.assertRaises(ManualImageError):
            self.submit(parameters={"prompt": "x" * 501, "seed": 7})
        self.assertEqual(self.mock.posts, 0)

    def test_gpu_worker_failure_fails_closed_without_request_submission(self):
        self.mock.fail_worker = True
        with self.assertRaises(ManualImageError) as caught:
            self.submit()
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(caught.exception.code, "comfyui_worker_unavailable")
        self.assertEqual(self.mock.posts, 0)

    def test_worker_device_is_unknown_when_comfyui_exposes_multiple_gpus(self):
        self.mock.devices = [{"name": "GPU 0"}, {"name": "GPU 1"}]
        worker = self.service.worker_status()
        self.assertEqual(worker["status"], "unknown")
        self.assertIsNone(worker["device"])
        with self.assertRaises(ManualImageError) as caught:
            self.submit()
        self.assertEqual(caught.exception.code, "comfyui_worker_unavailable")
        self.assertEqual(self.mock.posts, 0)

    def test_comfyui_execution_failure_is_durable_and_has_no_artifact(self):
        self.mock.fail_execution = True
        self.submit()
        record = self.wait()
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_code"], "workflow_execution_failed")
        self.assertIsNone(record["artifact"])

    def test_download_rechecks_artifact_bytes_after_independent_verification(self):
        self.submit()
        record = self.wait()
        path = Path(record["artifact"]["absolute_path"])
        path.write_bytes(PNG + b"changed")
        with self.assertRaises(ManualImageError) as caught:
            self.service.image_bytes(record["request_id"])
        self.assertEqual(caught.exception.code, "manual_artifact_integrity_failed")

    def test_completed_history_survives_service_reconstruction(self):
        self.submit()
        completed = self.wait()
        recovered = ManualImageGenerationService(endpoint=self.mock.endpoint,
            registry_path=ROOT / "deploy/comfyui/workflows.json",
            artifact_root=self.artifacts, state_root=self.state,
            timeout_seconds=5, poll_interval=0.1, output_host="test-controller")
        self.assertEqual(recovered.history("account-operator-1")[0]["request_id"],
                         completed["request_id"])
        self.assertEqual(self.mock.posts, 1)


if __name__ == "__main__":
    unittest.main()

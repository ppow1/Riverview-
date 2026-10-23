"""RIVERVIEW~ CONTROLLED SOURCE
File: tests/test_resource_telemetry.py
Component: STEWARD-DASHBOARD-RESOURCE-TELEMETRY
Revision: 1.1.1
Purpose: Verify bounded authenticated hardware and inference projections
Execution Model: Isolated unittest fixtures
Observability: Assertions for source status, redaction, readiness and unavailable data
Dependencies: DashboardResourceTelemetry and Python unittest
Authority: Disposable fixtures only; no production credentials or writes
Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Initial telemetry projection tests
Changed: 2026-10-22 UTC | RV-V2-HW-AI-ENHANCEMENTS-207 | Verify safe numeric slot context projection and raw task/prompt redaction
Changed: 2026-10-22 UTC | RV-V2-HW-AI-ENHANCEMENTS-207 | Keep context telemetry unavailable when slots contain no numeric context measurements
Contracts: docs/components/STATUS_DASHBOARD.md
Tests: python -m unittest tests.test_resource_telemetry
History: Git and .riverview-backups/manifest.jsonl
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from riverview_core.status_dashboard.resource_telemetry import DashboardResourceTelemetry


class ResourceTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.credentials = Path(self.temp.name)
        for name in ("resource-telemetry-key", "resource-telemetry-known-hosts"):
            path = self.credentials / name
            path.write_text("fixture-only")
            path.chmod(0o600)

    def tearDown(self):
        self.temp.cleanup()

    def test_gpu_projection_uses_strict_fixed_ssh_and_redacts_host_identifiers(self):
        payload = {
            "schema_version": "rv.gpu-host-telemetry.v1",
            "observed_at": "2026-10-21T17:10:00Z",
            "devices": [{
                "index": 0, "name": "Tesla P100-PCIE-16GB",
                "uuid": "GPU-secret-uuid", "pid": 12345,
                "utilization_percent": 82, "memory_used_bytes": 10,
                "memory_total_bytes": 20, "temperature_celsius": 49,
                "power_watts": 60.0, "fan_percent": None,
                "active_services": ["grace-reasoning-80b", "evil"],
            }],
        }
        def runner(command, **kwargs):
            self.assertIn("StrictHostKeyChecking=yes", command)
            self.assertIn("IdentitiesOnly=yes", command)
            self.assertIn("resource-telemetry", command)
            self.assertEqual(kwargs["timeout"], 5.0)
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        telemetry = DashboardResourceTelemetry(
            runner=runner, credential_directory=self.credentials, http_open=lambda *_a, **_k: None)
        result = telemetry._gpu_source()
        self.assertEqual(result["state"], "healthy")
        device = result["devices"][0]
        self.assertEqual(device["name"], "Tesla P100-PCIE-16GB")
        self.assertEqual(device["active_services"], ["grace-reasoning-80b"])
        serialized = json.dumps(result)
        for forbidden in ("GPU-secret-uuid", "12345"):
            self.assertNotIn(forbidden, serialized)

    def test_missing_credentials_fails_closed_without_running_ssh(self):
        with tempfile.TemporaryDirectory() as empty:
            def runner(*_args, **_kwargs):
                self.fail("SSH must not run without systemd credentials")
            result = DashboardResourceTelemetry(
                runner=runner, credential_directory=empty)._gpu_source()
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["error_code"], "telemetry_credentials_unavailable")

    def test_model_readiness_and_bounded_slot_context_are_projected_without_raw_fields(self):
        telemetry = DashboardResourceTelemetry(credential_directory=self.credentials)
        def read(url):
            if url.endswith("/health"):
                return {"status": "ok"}
            if url.endswith("/v1/models"):
                return {"data": [{"id": "/models/Qwen3-Next-80B.gguf"}]}
            return [{"id": 7, "id_task": 987654, "is_processing": True,
                     "n_ctx": 16384, "n_prompt_tokens": 3054,
                     "n_prompt_tokens_processed": 116, "n_prompt_tokens_cache": 40,
                     "prompt": "private prompt", "next_token": "private token"},
                    {"id": 8, "id_task": 123456, "is_processing": False,
                     "n_ctx": 16384, "n_prompt_tokens": 32,
                     "n_prompt_tokens_processed": 32, "n_prompt_tokens_cache": 0}]
        telemetry._read_json = read
        source = {
            "service_id": "grace-reasoning-80b", "display_name": "Grace reasoning 80B",
            "endpoint_id": "octominer1-llama-8080", "base_url": "http://127.0.0.1:8080",
        }
        result = telemetry._model_source(source)
        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["loaded_models"], ["Qwen3-Next-80B.gguf"])
        self.assertEqual(result["active_slots"]["value"], 1)
        self.assertIsNone(result["queued_requests"]["value"])
        self.assertEqual(result["slot_context"]["state"], "measured")
        self.assertEqual(result["slot_context"]["slots"][0], {
            "slot_id": 7, "processing": True, "context_tokens": 16384,
            "prompt_tokens": 3054, "prompt_tokens_processed": 116,
            "prompt_tokens_cached": 40,
        })
        self.assertEqual(result["slot_context"]["kv_cache_bytes"], {
            "state": "unavailable", "value": None,
            "reason": "not_exposed_by_current_model_server"})
        self.assertNotIn("private prompt", json.dumps(result))
        self.assertNotIn("id_task", json.dumps(result))
        self.assertNotIn("next_token", json.dumps(result))
        self.assertNotIn("987654", json.dumps(result))

    def test_invalid_source_data_is_unavailable_not_fabricated(self):
        telemetry = DashboardResourceTelemetry(credential_directory=self.credentials)
        telemetry._read_json = lambda _url: {"status": "not-ready"}
        source = {
            "service_id": "grace-vision-30b", "display_name": "Grace vision 30B",
            "endpoint_id": "octominer1-vision-18080", "base_url": "http://127.0.0.1:18080",
        }
        result = telemetry._model_source(source)
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["loaded_models"], [])
        self.assertIsNone(result["active_slots"]["value"])
        self.assertEqual(result["slot_context"]["state"], "unavailable")
        self.assertEqual(result["slot_context"]["slots"], [])

    def test_invalid_slot_counters_remain_unavailable_instead_of_becoming_zero(self):
        telemetry = DashboardResourceTelemetry(credential_directory=self.credentials)
        telemetry._read_json = lambda url: (
            {"status": "ok"} if url.endswith("/health") else
            {"data": [{"id": "model-1"}]} if url.endswith("/v1/models") else
            [{"id": 0, "is_processing": False, "n_ctx": "bad",
              "n_prompt_tokens": None, "n_prompt_tokens_processed": -1}])
        source = {"service_id": "grace-vision-30b", "display_name": "Grace vision 30B",
                  "endpoint_id": "test", "base_url": "http://127.0.0.1:18080"}
        slot = telemetry._model_source(source)["slot_context"]["slots"][0]
        self.assertIsNone(slot["context_tokens"])
        self.assertIsNone(slot["prompt_tokens"])
        self.assertIsNone(slot["prompt_tokens_processed"])
        self.assertEqual(telemetry._model_source(source)["slot_context"]["state"], "unavailable")

    def test_gpu_schema_rejects_invalid_shape(self):
        payload = {"schema_version": "wrong", "devices": []}
        runner = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        result = DashboardResourceTelemetry(runner=runner, credential_directory=self.credentials)._gpu_source()
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["error_code"], "gpu_source_schema_invalid")


if __name__ == "__main__":
    unittest.main()

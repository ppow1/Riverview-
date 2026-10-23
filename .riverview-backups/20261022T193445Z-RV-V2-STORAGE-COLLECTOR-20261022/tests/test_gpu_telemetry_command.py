"""RIVERVIEW~ CONTROLLED SOURCE
File: tests/test_gpu_telemetry_command.py
Component: OCTOMINER1-RESTRICTED-GPU-TELEMETRY
Revision: 1.0.0
Purpose: Verify the forced read-only host collector and identifier redaction
Execution Model: Isolated subprocess fixtures
Observability: Assertions for NVIDIA CSV mapping and unsupported values
Dependencies: scripts/rv_gpu_telemetry_command.py and Python unittest
Authority: Disposable fixtures only; no production host access
Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Initial collector tests
Contracts: docs/components/STATUS_DASHBOARD.md
Tests: python -m unittest tests.test_gpu_telemetry_command
History: Git and .riverview-backups/manifest.jsonl
"""
import os
import unittest
from unittest.mock import patch

from scripts.rv_gpu_telemetry_command import collect


class CollectorTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_rejects_invocation_without_forced_command_marker(self):
        with self.assertRaises(PermissionError):
            collect()

    @patch.dict(os.environ, {"SSH_ORIGINAL_COMMAND": "resource-telemetry"}, clear=True)
    @patch("scripts.rv_gpu_telemetry_command._run")
    def test_collects_measurements_and_only_allowlisted_service_labels(self, run):
        run.side_effect = [
            "Tesla P100-PCIE-16GB, 0, GPU-private-uuid, 40, 8192, 16384, 50, 70.1, N/A\n",
            "GPU-private-uuid, 321\n",
            "321\n", "0\n",
        ]
        with patch("scripts.rv_gpu_telemetry_command._SERVICE_LABELS", {
                "llama-server.service": "grace-reasoning-80b",
                "grace-vision.service": "grace-vision-30b"}):
            result = collect()
        self.assertEqual(result["schema_version"], "rv.gpu-host-telemetry.v1")
        gpu = result["devices"][0]
        self.assertEqual(gpu["memory_used_bytes"], 8192 * 1024 * 1024)
        self.assertEqual(gpu["active_services"], ["grace-reasoning-80b"])
        self.assertNotIn("uuid", gpu)
        self.assertNotIn("pid", gpu)
        self.assertIsNone(gpu["fan_percent"])

    @patch.dict(os.environ, {"SSH_ORIGINAL_COMMAND": "resource-telemetry"}, clear=True)
    @patch("scripts.rv_gpu_telemetry_command._run")
    def test_nvidia_bracketed_na_fan_does_not_drop_a_gpu(self, run):
        run.side_effect = [
            "Tesla P100-PCIE-16GB, 0, GPU-private-uuid, 17, 13286, 16384, 49, 59.97, [N/A]\n",
            "No running processes found\n", "0\n", "0\n",
        ]
        result = collect()
        self.assertEqual(len(result["devices"]), 1)
        self.assertEqual(result["devices"][0]["name"], "Tesla P100-PCIE-16GB")
        self.assertIsNone(result["devices"][0]["fan_percent"])


if __name__ == "__main__":
    unittest.main()

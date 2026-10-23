"""RIVERVIEW~ CONTROLLED SOURCE
File: tests/test_gpu_telemetry_command.py
Component: OCTOMINER1-RESTRICTED-GPU-TELEMETRY
Revision: 1.2.0
Purpose: Verify the forced read-only host collector and identifier redaction
Execution Model: Isolated subprocess fixtures
Observability: Assertions for NVIDIA CSV mapping, mounted storage, and unsupported values
Dependencies: scripts/rv_gpu_telemetry_command.py and Python unittest
Authority: Disposable fixtures only; no production host access
Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Initial collector tests
Changed: 2026-10-22 UTC | RV-V2-STORAGE-CAPACITY-001 | Verify mounted storage is included without pseudo-filesystems or duplicate mounts.
Changed: 2026-10-22 UTC | RV-V2-MOUNTED-STORAGE-001 | Verify optional mount enumeration failure does not suppress GPU measurements.
Changed: 2026-10-22 UTC | ISSUE-231 | Verify bounded timestamped host CPU and RAM collector fields.
Contracts: docs/components/STATUS_DASHBOARD.md
Tests: python -m unittest tests.test_gpu_telemetry_command
History: Git and .riverview-backups/manifest.jsonl
"""
import os
import unittest
from unittest.mock import patch

from scripts.rv_gpu_telemetry_command import collect


class CollectorTests(unittest.TestCase):
    def test_host_metrics_report_bounded_cpu_ram_and_a_timestamp(self):
        from scripts.rv_gpu_telemetry_command import _host_metrics
        result = _host_metrics()
        self.assertRegex(result["observed_at"], r"^\d{4}-\d\d-\d\dT.*Z$")
        self.assertTrue(result["cpu_name"] == "Unavailable" or len(result["cpu_name"]) <= 100)
        cpu = result["cpu_utilization_percent"]
        self.assertTrue(cpu is None or 0 <= cpu <= 100)
        total, used = result["memory_total_bytes"], result["memory_used_bytes"]
        self.assertTrue((total is None and used is None) or
                        (type(total) is int and type(used) is int and 0 <= used <= total))

    @patch.dict(os.environ, {}, clear=True)
    def test_rejects_invocation_without_forced_command_marker(self):
        with self.assertRaises(PermissionError):
            collect()

    @patch.dict(os.environ, {"SSH_ORIGINAL_COMMAND": "resource-telemetry"}, clear=True)
    @patch("scripts.rv_gpu_telemetry_command._storage_volumes", return_value=[])
    @patch("scripts.rv_gpu_telemetry_command._run")
    def test_collects_measurements_and_only_allowlisted_service_labels(self, run, _storage):
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
        self.assertEqual(result["storage_volumes"], [])

    @patch.dict(os.environ, {"SSH_ORIGINAL_COMMAND": "resource-telemetry"}, clear=True)
    @patch("scripts.rv_gpu_telemetry_command._storage_volumes", side_effect=OSError("mount table unavailable"))
    @patch("scripts.rv_gpu_telemetry_command._run")
    def test_storage_failure_does_not_hide_gpu_telemetry(self, run, _storage):
        run.side_effect = [
            "Tesla P100-PCIE-16GB, 0, GPU-private-uuid, 40, 8192, 16384, 50, 70.1, N/A\n",
            "No running processes found\n", "0\n", "0\n",
        ]
        result=collect()
        self.assertEqual(len(result["devices"]),1)
        self.assertEqual(result["storage_volumes"],[])

    @patch.dict(os.environ, {"SSH_ORIGINAL_COMMAND": "resource-telemetry"}, clear=True)
    @patch("scripts.rv_gpu_telemetry_command._storage_volumes", return_value=[])
    @patch("scripts.rv_gpu_telemetry_command._run")
    def test_nvidia_bracketed_na_fan_does_not_drop_a_gpu(self, run, _storage):
        run.side_effect = [
            "Tesla P100-PCIE-16GB, 0, GPU-private-uuid, 17, 13286, 16384, 49, 59.97, [N/A]\n",
            "No running processes found\n", "0\n", "0\n",
        ]
        result = collect()
        self.assertEqual(len(result["devices"]), 1)
        self.assertEqual(result["devices"][0]["name"], "Tesla P100-PCIE-16GB")
        self.assertIsNone(result["devices"][0]["fan_percent"])

    def test_storage_collector_deduplicates_bind_mounts_and_skips_overlay(self):
        from scripts.rv_gpu_telemetry_command import _storage_volumes
        from tempfile import NamedTemporaryFile
        mountinfo = """36 25 8:1 / / rw,relatime - ext4 /dev/sda1 rw
37 36 8:1 /data /mnt/data rw,relatime - ext4 /dev/sda1 rw
38 25 0:42 / /var/lib/container rw,relatime - overlay overlay rw
"""
        with NamedTemporaryFile(mode="w", encoding="utf-8") as file:
            file.write(mountinfo)
            file.flush()
            with patch("scripts.rv_gpu_telemetry_command.os.statvfs") as statvfs:
                statvfs.return_value.f_frsize = 4096
                statvfs.return_value.f_bsize = 4096
                statvfs.return_value.f_blocks = 100
                statvfs.return_value.f_bfree = 40
                statvfs.return_value.f_bavail = 30
                result = _storage_volumes(file.name)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["mount_point"], "/")
        self.assertEqual(result[0]["also_mounted_at"], ["/mnt/data"])
        self.assertEqual(result[0]["total_bytes"], 409600)
        self.assertEqual(result[0]["used_bytes"], 245760)
        self.assertEqual(result[0]["available_bytes"], 122880)


if __name__ == "__main__":
    unittest.main()

"""RIVERVIEW~ CONTROLLED SOURCE
File: tests/test_issue231_optional_hosts.py
Component: STEWARD-DASHBOARD-RESOURCE-TELEMETRY
Revision: 1.0.0
Purpose: Verify pinned optional Windows/OCTO2 telemetry and honest unavailable states
Execution Model: Isolated unittest fixtures
Observability: Bounded host projection, strict SSH options, and no fabricated readings
Dependencies: DashboardResourceTelemetry and unittest
Authority: Fixture-only; no production SSH credentials or writes
Changed: 2026-10-23 UTC | ISSUE-242 | Initial optional-host integration tests
Contracts: docs/components/STATUS_DASHBOARD.md
History: Git and revision/backup manifest
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from riverview_core.status_dashboard.resource_telemetry import DashboardResourceTelemetry


class OptionalHostTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.credentials = Path(self.directory.name)
        for name, value in (
            ("resource-telemetry-octo2-key", "fixture-key"),
            ("resource-telemetry-octo2-known-hosts", "fixture-host-key"),
            ("resource-telemetry-octo2-user", "root"),
        ):
            (self.credentials / name).write_text(value, encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    @staticmethod
    def host():
        return {"host_id": "octominer2", "display_name": "OCTO2",
                "address": "192.168.1.162", "command": "resource-telemetry",
                "credential_prefix": "resource-telemetry-octo2",
                "identity_state": "documented_unverified"}

    def test_unconfigured_optional_host_is_unavailable_without_ssh(self):
        telemetry = DashboardResourceTelemetry(credential_directory=self.credentials)
        def fail(*_args, **_kwargs):
            self.fail("Optional host must not be contacted without its pinned credentials")
        telemetry._runner = fail
        (self.credentials / "resource-telemetry-octo2-key").unlink()
        result = telemetry._optional_host_source(self.host())
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["devices"], [])
        self.assertIsNone(result["system_metrics"]["cpu_utilization_percent"])
        self.assertEqual(result["storage"]["volumes"], [])
        self.assertEqual(result["error_code"], "host_telemetry_credentials_unavailable")

    def test_offline_octo2_is_unavailable_not_zero_and_uses_pinned_read_only_ssh(self):
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 255, "", "connection refused")
        telemetry = DashboardResourceTelemetry(runner=runner, credential_directory=self.credentials)
        result = telemetry._optional_host_source(self.host())
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["devices"], [])
        self.assertEqual(result["storage"]["volumes"], [])
        self.assertIsNone(result["system_metrics"]["memory_total_bytes"])
        self.assertEqual(result["error_code"], "host_telemetry_unreachable")
        command, options = calls[0]
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertIn("GlobalKnownHostsFile=/dev/null", command)
        self.assertIn("IdentitiesOnly=yes", command)
        self.assertIn("root@192.168.1.162", command)
        self.assertEqual(command[-1], "resource-telemetry")
        self.assertEqual(options["timeout"], 5.0)
        self.assertNotIn("connection refused", json.dumps(result))

    def test_optional_host_projects_only_bounded_measurements(self):
        payload = {"schema_version": "rv.gpu-host-telemetry.v1",
                   "observed_at": "2026-10-23T10:00:00Z",
                   "host_metrics": {"observed_at": "2026-10-23T10:00:00Z",
                                    "cpu_name": "Example CPU", "cpu_utilization_percent": 31.25,
                                    "memory_total_bytes": 1000, "memory_used_bytes": 600,
                                    "private": "discard"},
                   "devices": [{"index": 0, "name": "Example GPU", "utilization_percent": 44,
                                "memory_used_bytes": 400, "memory_total_bytes": 1000,
                                "temperature_celsius": 50, "power_watts": 120.5,
                                "fan_percent": 30, "uuid": "private", "pid": 900}],
                   "storage_volumes": []}
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        telemetry = DashboardResourceTelemetry(runner=runner, credential_directory=self.credentials)
        result = telemetry._optional_host_source(self.host())
        self.assertEqual(result["state"], "healthy")
        self.assertEqual(result["system_metrics"]["cpu_utilization_percent"], 31.25)
        self.assertEqual(result["system_metrics"]["memory_used_bytes"], 600)
        self.assertEqual(result["devices"][0]["utilization_percent"], 44)
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(calls[0][-2:], ["root@192.168.1.162", "resource-telemetry"])

    def test_windows_username_is_bounded_and_invalid_payload_is_unavailable(self):
        (self.credentials / "resource-telemetry-octo2-user").write_text("bad;command", encoding="utf-8")
        telemetry = DashboardResourceTelemetry(credential_directory=self.credentials,
                                               runner=lambda *_a, **_k: self.fail("must not connect"))
        result = telemetry._optional_host_source(self.host())
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["error_code"], "host_telemetry_credentials_unavailable")


if __name__ == "__main__":
    unittest.main()

"""RIVERVIEW~ CONTROLLED SOURCE
File: tests/test_storage_inventory.py
Component: STEWARD-DASHBOARD-RESOURCE-TELEMETRY
Revision: 1.0.1
Changed: 2026-10-22 UTC | RV-V2-MOUNTED-STORAGE-001 | Correct fake statvfs mount fixture for bind alias verification.
Purpose: Verify read-only mounted-volume inventory and remote payload validation
Execution Model: Isolated unittest fixtures
Observability: Assertions cover measured capacity, deduplication, and unavailable outcomes
Dependencies: status_dashboard.storage_inventory and Python unittest
Authority: Temporary fixture mountinfo only; no production filesystem or credentials
Changed: 2026-10-22 UTC | RV-V2-STORAGE-CAPACITY-001 | Initial storage inventory regressions
Contracts: docs/components/STATUS_DASHBOARD.md
Tests: python -m unittest tests.test_storage_inventory
History: Git and .riverview-backups/manifest.jsonl
"""
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from riverview_core.status_dashboard.storage_inventory import collect_linux_storage, project_remote_volumes


class StorageInventoryTests(unittest.TestCase):
    def test_collects_realistic_volume_rows_and_deduplicates_bind_mounts(self):
        mountinfo = """36 25 8:1 / / rw,relatime - ext4 /dev/sda1 rw
37 36 8:1 /data /mnt/data rw,relatime - ext4 /dev/sda1 rw
38 25 0:42 / /var/lib/container rw,relatime - overlay overlay rw
39 25 0:43 / /run rw,relatime - tmpfs tmpfs rw
40 25 0:71 / //server/share rw,relatime - nfs4 server:/exports/data rw
"""
        def statvfs(path):
            if path in {"/", "/mnt/data"}: return SimpleNamespace(f_frsize=4096, f_bsize=4096, f_blocks=100, f_bfree=40, f_bavail=30)
            if path == "//server/share": return SimpleNamespace(f_frsize=1024, f_bsize=1024, f_blocks=200, f_bfree=80, f_bavail=75)
            raise OSError("not mounted")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as source:
            source.write(mountinfo)
            source.flush()
            result = collect_linux_storage("camrui", mountinfo_path=source.name, statvfs=statvfs)
        self.assertEqual(result["state"], "healthy")
        self.assertEqual(len(result["volumes"]), 2)
        local = next(item for item in result["volumes"] if item["filesystem_type"] == "ext4")
        self.assertEqual(local["mount_point"], "/")
        self.assertEqual(local["also_mounted_at"], ["/mnt/data"])
        self.assertEqual(local["total_bytes"], 409600)
        self.assertEqual(local["used_bytes"], 245760)
        self.assertEqual(local["available_bytes"], 122880)
        network = next(item for item in result["volumes"] if item["filesystem_type"] == "nfs4")
        self.assertTrue(network["filesystem_id"].startswith("shared:nfs4:"))

    def test_unavailable_mounts_are_not_reported_as_zero_capacity(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as source:
            source.write("36 25 8:1 / / rw - ext4 /dev/sda1 rw\n")
            source.flush()
            result = collect_linux_storage("camrui", mountinfo_path=source.name,
                                          statvfs=lambda _path: (_ for _ in ()).throw(OSError()))
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["volumes"], [])
        self.assertIsNotNone(result["error_code"])

    def test_remote_collector_rows_are_bounded_and_validated(self):
        valid = {"major_minor": "8:1", "filesystem_type": "ext4", "source": "/dev/sda1",
                 "mount_point": "/data", "total_bytes": 1000, "used_bytes": 400,
                 "available_bytes": 500}
        result = project_remote_volumes("octominer1", {"observed_at": "2026-10-22T19:00:00Z",
                                                        "storage_volumes": [valid, valid,
                                                          {**valid, "total_bytes": -1},
                                                          {**valid, "filesystem_type": "overlay"}]})
        self.assertEqual(result["state"], "healthy")
        self.assertEqual(len(result["volumes"]), 1)
        self.assertEqual(result["volumes"][0]["percent_used"], 40.0)
        missing = project_remote_volumes("octominer1", {"devices": []})
        self.assertEqual(missing["state"], "unavailable")
        self.assertEqual(missing["error_code"], "storage_source_not_reporting")


if __name__ == "__main__":
    unittest.main()

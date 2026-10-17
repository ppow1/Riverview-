"""Immutable Comms5 source package builder tests.

File Revision: 1.0.0
Component: COMMS5-CAMRUI-PACKAGING-TESTS
History: New file; no predecessor existed.
"""

import hashlib
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.package_comms5_camrui import PACKAGE_FILES, build


class Comms5PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def repository(self) -> Path:
        root = self.tmp_path / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Comms5 Test"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "comms5-test@example.invalid"], check=True)
        for name in PACKAGE_FILES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("package test fixture: " + name + "\n")
        subprocess.run(["git", "-C", str(root), "add", *PACKAGE_FILES], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "package fixture"], check=True)
        return root

    def test_package_is_source_pinned_complete_and_deterministic(self):
        root = self.repository()
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        first, second = self.tmp_path / "first.tar.gz", self.tmp_path / "second.tar.gz"
        first_result = build(root, first)
        second_result = build(root, second)
        self.assertEqual(first_result, (commit, second_result[1]))
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with tarfile.open(first, "r:gz") as archive:
            entries = {item.name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile()}
        self.assertEqual(entries["SOURCE_COMMIT"].decode().strip(), commit)
        manifest = json.loads(entries["COMMS5_PACKAGE.json"])
        self.assertEqual(manifest["source_commit"], commit)
        self.assertEqual({item["path"] for item in manifest["files"]}, set(PACKAGE_FILES))
        for item in manifest["files"]:
            self.assertEqual(hashlib.sha256(entries[item["path"]]).hexdigest(), item["sha256"])
        for line in entries["PACKAGE_SHA256SUMS"].decode().splitlines():
            digest, path = line.split("  ", 1)
            self.assertEqual(hashlib.sha256(entries[path]).hexdigest(), digest)

    def test_package_rejects_output_inside_checkout_and_existing_output(self):
        root = self.repository()
        with self.assertRaisesRegex(ValueError, "outside_checkout"):
            build(root, root / "package.tar.gz")
        outside = self.tmp_path / "existing.tar.gz"
        outside.write_bytes(b"preserve")
        with self.assertRaises(FileExistsError):
            build(root, outside)

    def test_package_requires_clean_worktree_for_default_revision(self):
        root = self.repository()
        (root / PACKAGE_FILES[0]).write_text("mutable\n")
        with self.assertRaises(subprocess.CalledProcessError):
            build(root, self.tmp_path / "dirty.tar.gz")


if __name__ == "__main__":
    unittest.main()

"""Immutable Comms5 source package builder tests.

File Revision: 1.0.0
Component: COMMS5-CAMRUI-PACKAGING-TESTS
History: New file; no predecessor existed.
"""

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from scripts.package_comms5_camrui import PACKAGE_FILES, build


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
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


def test_package_is_source_pinned_complete_and_deterministic(tmp_path):
    root = repository(tmp_path)
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    assert build(root, first) == (commit, build(root, second)[1])
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as archive:
        entries = {item.name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile()}
    assert entries["SOURCE_COMMIT"].decode().strip() == commit
    manifest = json.loads(entries["COMMS5_PACKAGE.json"])
    assert manifest["source_commit"] == commit
    assert {item["path"] for item in manifest["files"]} == set(PACKAGE_FILES)
    for item in manifest["files"]:
        assert hashlib.sha256(entries[item["path"]]).hexdigest() == item["sha256"]
    for line in entries["PACKAGE_SHA256SUMS"].decode().splitlines():
        digest, path = line.split("  ", 1)
        assert hashlib.sha256(entries[path]).hexdigest() == digest


def test_package_rejects_output_inside_checkout_and_existing_output(tmp_path):
    root = repository(tmp_path)
    with pytest.raises(ValueError, match="outside_checkout"):
        build(root, root / "package.tar.gz")
    outside = tmp_path / "existing.tar.gz"
    outside.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        build(root, outside)


def test_package_requires_clean_worktree_for_default_revision(tmp_path):
    root = repository(tmp_path)
    (root / PACKAGE_FILES[0]).write_text("mutable\n")
    with pytest.raises(subprocess.CalledProcessError):
        build(root, tmp_path / "dirty.tar.gz")

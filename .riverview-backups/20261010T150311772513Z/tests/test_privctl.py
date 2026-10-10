# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_privctl.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Reject unsafe package provenance, archive members and command identifiers
# Execution Model: Request-driven isolated unit tests
# Observability: unittest results; no privileged host changes
# Dependencies: Python 3.10+, standard library
# Authority: Temporary in-memory archives only; no system command execution
# Changed: 2026-10-10 UTC | RV-M1.1-009 | Initial privilege-broker regression coverage
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: This file
# History: Git + .riverview-backups/manifest.jsonl
# =============================================================================
import hashlib
import io
from contextlib import redirect_stderr
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import riverview_privctl as privctl


COMMIT = "a" * 40


def package(entries=None, manifest_override=None):
    entries = dict(entries or {
        "SOURCE_COMMIT": (COMMIT + "\n").encode(),
        "deploy/install_baseline.sh": b"#!/bin/sh\nexit 0\n",
        "deploy/rollback_baseline.sh": b"#!/bin/sh\nexit 0\n",
        "deploy/systemd/riverview-baseline.service": b"[Service]\n",
        "scripts/capture_baseline_acceptance.py": b"pass\n",
    })
    checksums = manifest_override or "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                                               for name, data in entries.items())
    entries["PACKAGE_SHA256SUMS"] = checksums.encode()
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as tar:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            tar.addfile(info, io.BytesIO(data))
    return output.getvalue()


class PrivilegedBrokerPackageTests(unittest.TestCase):
    def validate(self, blob=None, commit=COMMIT):
        blob = package() if blob is None else blob
        return privctl.validated_members(blob, hashlib.sha256(blob).hexdigest(), commit)

    def test_exact_manifest_and_approved_commit_are_required(self):
        self.assertEqual(len(self.validate()), 6)
        blob = package()
        with self.assertRaisesRegex(privctl.BrokerError, "package_digest_mismatch"):
            privctl.validated_members(blob, "0" * 64, COMMIT)
        with self.assertRaisesRegex(privctl.BrokerError, "package_commit_mismatch"):
            self.validate(blob, "b" * 40)

    def test_path_traversal_and_symbolic_links_are_rejected(self):
        for name, kind in (("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE),
                           ("link", tarfile.SYMTYPE)):
            blob = io.BytesIO()
            with tarfile.open(fileobj=blob, mode="w:gz") as tar:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.linkname = "target"
                if kind == tarfile.REGTYPE:
                    info.size = 0
                    tar.addfile(info, io.BytesIO())
                else:
                    tar.addfile(info)
            raw = blob.getvalue()
            with self.subTest(member=name), self.assertRaises(privctl.BrokerError):
                privctl.validated_members(raw, hashlib.sha256(raw).hexdigest(), COMMIT)

    def test_manifest_tampering_and_duplicate_paths_are_rejected(self):
        values = {"SOURCE_COMMIT": (COMMIT + "\n").encode(),
                  "deploy/install_baseline.sh": b"#!/bin/sh\nfalse\n",
                  "deploy/rollback_baseline.sh": b"#!/bin/sh\nexit 0\n",
                  "deploy/systemd/riverview-baseline.service": b"[Service]\n",
                  "scripts/capture_baseline_acceptance.py": b"pass\n"}
        install_digest = hashlib.sha256(values["deploy/install_baseline.sh"]).hexdigest()
        bad_digest = ("0" if install_digest[0] != "0" else "1") + install_digest[1:]
        blob = package(values, bad_digest + "  deploy/install_baseline.sh\n" +
                       "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                               for name, data in values.items() if name != "deploy/install_baseline.sh"))
        with self.assertRaises(privctl.BrokerError):
            self.validate(blob)

        duplicate = io.BytesIO()
        with tarfile.open(fileobj=duplicate, mode="w:gz") as tar:
            for name, data in (("file", b"one"), ("file", b"two")):
                item = tarfile.TarInfo(name); item.size = len(data); tar.addfile(item, io.BytesIO(data))
        raw = duplicate.getvalue()
        with self.assertRaisesRegex(privctl.BrokerError, "unsafe_package_member"):
            privctl.validated_members(raw, hashlib.sha256(raw).hexdigest(), COMMIT)

    def test_only_fixed_service_actions_and_constrained_identifiers_are_admitted(self):
        self.assertEqual(privctl.UNIT, "riverview-baseline.service")
        self.assertTrue(privctl.PACKAGE_ID.fullmatch("initial-m11"))
        self.assertFalse(privctl.PACKAGE_ID.fullmatch("../../other"))
        self.assertTrue(privctl.BACKUP_ID.fullmatch("riverview-baseline.ABCDef123456"))
        self.assertFalse(privctl.BACKUP_ID.fullmatch("/tmp/anything"))
        self.assertEqual(set(("start", "stop", "restart", "status")),
                         {x for x in ("start", "stop", "restart", "status")})
        self.assertEqual(privctl.parse_args(["service", "restart"]).action, "restart")
        for argv in (("run", "bash"), ("service", "restart", "arbitrary-unit"),
                     ("accept", "--output", "/tmp/evidence")):
            diagnostic = io.StringIO()
            with self.subTest(argv=argv), redirect_stderr(diagnostic), self.assertRaises(SystemExit):
                privctl.parse_args(argv)
            self.assertEqual(diagnostic.getvalue(), "riverview-privctl: invalid request\n")
        with self.assertRaisesRegex(privctl.BrokerError, "invalid_package_id"):
            privctl.install_package("../../etc/shadow")
        with self.assertRaisesRegex(privctl.BrokerError, "invalid_rollback_record"):
            privctl.rollback("/tmp/record")

    def test_service_operation_constructs_only_fixed_unit_argv(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append(argv)
            return type("Completed", (), {"returncode": 0, "stdout": "active\n", "stderr": ""})()
        result = privctl.service("status", runner=runner)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(calls, [["/usr/bin/systemctl", "status", "riverview-baseline.service"]])

    def test_release_root_cannot_be_redirected_to_caller_path(self):
        with self.assertRaisesRegex(privctl.BrokerError, "unexpected_release_root"):
            privctl.ensure_release_parent(Path("/tmp/user-controlled/releases"))

    def test_only_virtual_environment_runtime_symlinks_are_trusted(self):
        with tempfile.TemporaryDirectory() as folder:
            release = Path(folder)
            (release/".venv/lib").mkdir(parents=True)
            (release/".venv/bin").mkdir()
            (release/".venv/lib64").symlink_to("lib")
            (release/".venv/bin/python").symlink_to("python3")
            (release/".venv/bin/python3.12").symlink_to("python3")
            (release/".venv/bin/python3").symlink_to("/usr/bin/python3")
            for relative in privctl.VENV_SYMLINKS:
                privctl.validate_release_symlink(release, release/relative)
            (release/".venv/bin/escape").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(privctl.BrokerError, "unexpected_release_symlink"):
                privctl.validate_release_symlink(release, release/".venv/bin/escape")


if __name__ == "__main__":
    unittest.main()

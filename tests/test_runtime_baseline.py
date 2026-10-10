# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_runtime_baseline.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.1
# Purpose: Identity/credential security, DB contract, observer and package regression tests
# Execution Model: Request-driven tests; simulated DB explicitly distinct from live proof
# Observability: unittest counts and failures
# Dependencies: Python 3.10+, Git, Linux
# Authority: Temporary fixtures only; no live DB or credentials
# Changed: 2026-10-10 UTC | RV-M1.1-002 | Exercise packaged Linux shells under Windows Git settings
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: This file
# History: docs/history/RV-M1.1-002/rev1.0.0/tests/test_runtime_baseline.py
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import runtime_baseline as baseline
from capture_baseline_acceptance import capture
from build_camrui_package import build
from check_camrui_baseline import command
from provision_pgpass import pgpass_line
from read_baseline_report import read_report
from verify_camrui_package import verify


class RuntimeBaselineTests(unittest.TestCase):
    def run_probe(self, rows=None, failure=None, identity=None, environ=None):
        connect = MagicMock()
        cur = connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect = rows or [("on",), ("riverview_core", "riverview", "127.0.0.1"),
                                          (False,) * 5, ("riverview_core", True, True)]
        if failure:
            connect.side_effect = failure
        account = identity or SimpleNamespace(pw_uid=12345, pw_shell="/usr/sbin/nologin")
        with patch.object(baseline.pwd, "getpwnam", return_value=account), \
             patch.object(baseline.os, "geteuid", return_value=12345), \
             patch.object(baseline, "private_path"), \
             patch.dict(os.environ, environ or {}, clear=True):
            report, code = baseline.probe(passfile=Path("/credentials/pgpass"),
                                          state_dir=Path("/var/lib/riverview"), connect=connect)
        return report, code, connect, cur

    def test_valid_baseline_is_not_institutional_health(self):
        report, code, connect, cur = self.run_probe()
        self.assertEqual(code, 0)
        self.assertTrue(report["baseline_ready"])
        self.assertEqual(report["institutional_readiness"], "not_verified")
        self.assertIsNone(report["heartbeat_at"])
        kwargs = connect.call_args.kwargs
        self.assertEqual(kwargs["options"], "-c default_transaction_read_only=on")
        self.assertNotIn("password", kwargs)
        for call in cur.execute.call_args_list:
            self.assertTrue(call.args[0].startswith(("SHOW", "SELECT")))

    def test_schema_owner_is_observed_without_inventing_an_ownership_migration(self):
        report, code, _, _ = self.run_probe(rows=[("on",), ("riverview_core", "riverview", "127.0.0.1"),
                                                (False,) * 5, ("postgres", True, True)])
        self.assertEqual(code, 0)
        self.assertEqual(report["schema_owner"], "postgres")

    def test_repeated_requests_are_independent(self):
        for _ in range(2):
            self.assertEqual(self.run_probe()[1], 0)

    def test_driver_error_is_sanitized(self):
        report, code, _, _ = self.run_probe(failure=RuntimeError("password=DO_NOT_LOG"))
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "unavailable")
        self.assertNotIn("DO_NOT_LOG", json.dumps(report))

    def test_role_and_schema_fail_closed(self):
        cases = [
            ([("off",)], "READ_ONLY_REQUIRED"),
            ([("on",), ("wrong", "riverview", "127.0.0.1")], "DATABASE_IDENTITY_MISMATCH"),
            ([("on",), ("riverview_core", "riverview", "127.0.0.1"), (True,) * 5], "EXCESS_DATABASE_PRIVILEGE"),
            ([("on",), ("riverview_core", "riverview", "127.0.0.1"), (False,) * 5, None], "SCHEMA_MISSING"),
            ([("on",), ("riverview_core", "riverview", "127.0.0.1"), (False,) * 5,
              ("other", True, False)], "SCHEMA_AUTHORITY_MISMATCH"),
        ]
        for rows, code in cases:
            with self.subTest(code=code):
                report, result, _, _ = self.run_probe(rows=rows)
                self.assertEqual(result, 2)
                self.assertEqual(report["blocker_code"], code)

    def test_service_identity_and_ambient_password_rejected(self):
        for identity, environ, code in [
            (SimpleNamespace(pw_uid=0, pw_shell="/usr/sbin/nologin"), {}, "IDENTITY_MISMATCH"),
            (SimpleNamespace(pw_uid=12345, pw_shell="/bin/bash"), {}, "INTERACTIVE_SERVICE_ACCOUNT"),
            (None, {"PGPASSWORD": "DO_NOT_LOG"}, "AMBIENT_DATABASE_OVERRIDE"),
        ]:
            report, result, connect, _ = self.run_probe(identity=identity, environ=environ)
            self.assertEqual(result, 2)
            self.assertEqual(report["blocker_code"], code)
            connect.assert_not_called()

    def test_secure_file_modes_symlink_empty_and_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pgpass"
            path.write_text("fixture")
            path.chmod(0o600)
            baseline.private_path(path, os.getuid())
            for mode in (0o644, 0o640):
                path.chmod(mode)
                with self.assertRaises(baseline.BaselineError):
                    baseline.private_path(path, os.getuid())
            path.chmod(0o600)
            with self.assertRaises(baseline.BaselineError):
                baseline.private_path(path, os.getuid() + 1)
            link = Path(folder) / "link"
            link.symlink_to(path)
            with self.assertRaises(baseline.BaselineError):
                baseline.private_path(link, os.getuid())
            path.write_text("")
            with self.assertRaises(baseline.BaselineError):
                baseline.private_path(path, os.getuid())

    def test_pgpass_escaping_and_invalid_passwords(self):
        self.assertEqual(pgpass_line("a:b\\c"), "127.0.0.1:5432:riverview:riverview_core:a\\:b\\\\c\n")
        for value in ("", "a\nb", "a\rb", "a\x00b"):
            with self.assertRaises(ValueError):
                pgpass_line(value)

    def test_observer_fresh_stale_missing_and_failure(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report"
            self.assertEqual(read_report(path, now)[1], 2)
            report = dict(projection_version="rv.runtime-baseline.v1", observed_at=now.isoformat(),
                          expires_at=(now + timedelta(seconds=60)).isoformat(),
                          baseline_ready=True, status="baseline_ready")
            path.write_text(json.dumps(report))
            self.assertEqual(read_report(path, now)[1], 0)
            stale, code = read_report(path, now + timedelta(seconds=60))
            self.assertEqual(code, 3)
            self.assertFalse(stale["baseline_ready"])
            report.update(status="blocked", baseline_ready=False)
            path.write_text(json.dumps(report))
            self.assertEqual(read_report(path, now)[1], 1)
            for invalid in ("incomplete", "[]", "null", "42"):
                path.write_text(invalid)
                self.assertEqual(read_report(path, now)[1], 2)

    def test_observer_rejects_future_and_excess_ttl(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report"
            for start, end in [(now + timedelta(seconds=1), now + timedelta(seconds=60)),
                               (now, now + timedelta(seconds=61))]:
                path.write_text(json.dumps(dict(projection_version="rv.runtime-baseline.v1",
                                               observed_at=start.isoformat(), expires_at=end.isoformat())))
                self.assertEqual(read_report(path, now)[1], 2)

    def test_ssh_command_and_injection_rejection(self):
        args = command("admin1@192.168.1.155")
        self.assertIn("StrictHostKeyChecking=yes", args)
        self.assertIn("BatchMode=yes", args)
        for value in ("-oProxyCommand=x", "host;id", "$(id)", "user@host path"):
            with self.assertRaises(ValueError):
                command(value)

    def test_acceptance_requires_fresh_distinct_matching_observations(self):
        commit = "a" * 40
        runner = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
        def reader(times, source=commit, code=0):
            return MagicMock(side_effect=[({"observed_at": t, "source_commit": source}, code) for t in times])
        report, code = capture(run=runner, read=reader(["one", "two"]), source_commit=commit)
        self.assertEqual(code, 0)
        self.assertEqual(report["step_acceptance"], "PENDING_STEWARD")
        self.assertEqual(report["full_component_dod"], "NOT_DONE")
        for read in (reader(["same", "same"]), reader(["one", "two"], source="b" * 40),
                     reader(["one", "two"], code=3)):
            self.assertEqual(capture(run=runner, read=read, source_commit=commit)[1], 1)
        runner.return_value.returncode = 1
        self.assertEqual(capture(run=runner, read=reader(["one", "two"]), source_commit=commit)[1], 1)

    def test_package_exact_commit_checksums_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "code.py").write_text("print('fixture')\n")
            (root / "untracked-secret").write_text("NEVER_PACKAGE")
            subprocess.run(["git", "-C", str(root), "add", "code.py"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
            output = Path(folder) / "package.tar.gz"
            commit, digest = build(root, output)
            self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())
            with tarfile.open(output) as archive:
                self.assertNotIn("untracked-secret", archive.getnames())
                self.assertEqual(archive.extractfile("SOURCE_COMMIT").read().decode().strip(), commit)
                manifest = archive.extractfile("PACKAGE_SHA256SUMS").read().decode().splitlines()
                for line in manifest:
                    checksum, name = line.split("  ", 1)
                    self.assertEqual(checksum, hashlib.sha256(archive.extractfile(name).read()).hexdigest())
            with self.assertRaises(FileExistsError):
                build(root, output)
            (root / "code.py").write_text("changed")
            with self.assertRaises(subprocess.CalledProcessError):
                build(root, Path(folder) / "dirty.tar.gz")


class PackageShellCompatibilityTests(unittest.TestCase):
    scripts = ("deploy/install_baseline.sh", "deploy/rollback_baseline.sh")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.contents = {}
        project = Path(__file__).resolve().parents[1]
        for name in self.scripts:
            content = (project / name).read_bytes()
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            self.contents[name] = content
        self.git("add", ".")
        self.git("commit", "-qm", "LF shell fixture")

    def git(self, *arguments):
        return subprocess.check_output(["git", "-C", str(self.root), *arguments])

    def extract_and_check(self, output):
        with tarfile.open(output) as package:
            for name in self.scripts:
                data = package.extractfile(name).read()
                self.assertEqual(data, self.git("cat-file", "blob", "HEAD:" + name))
                self.assertNotIn(b"\r", data)
                self.assertNotIn(b"\x00", data)
                self.assertTrue(data.startswith(b"#!/bin/sh\n"))
            manifest = package.extractfile("PACKAGE_SHA256SUMS").read().decode().splitlines()
            for line in manifest:
                checksum, name = line.split("  ", 1)
                self.assertEqual(checksum, hashlib.sha256(package.extractfile(name).read()).hexdigest())
            extracted = Path(self.temporary.name) / (output.stem + "-extracted")
            extracted.mkdir()
            # All files are synthetic fixtures produced by the tested builder.
            for name in self.scripts:
                target = extracted / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(package.extractfile(name).read())
        return extracted

    def test_packaged_bytes_ignore_windows_checkout_and_export_conversion(self):
        # Explicit attributes demonstrate why a Git configuration override alone
        # is insufficient to guarantee an exact committed-byte package.
        (self.root / ".gitattributes").write_bytes(b"*.sh text eol=crlf\n")
        self.git("add", ".gitattributes")
        self.git("commit", "-qm", "Windows export attributes")
        self.git("config", "core.autocrlf", "true")
        self.git("config", "core.eol", "crlf")
        for name, content in self.contents.items():
            (self.root / name).write_bytes(content.replace(b"\n", b"\r\n"))
        output = Path(self.temporary.name) / "windows.tar.gz"
        build(self.root, output)
        self.extract_and_check(output)
        report, code = verify(output)
        self.assertEqual(code, 0)
        self.assertEqual(report["manifest"], "PASS")
        self.assertTrue(all(item["cr_bytes"] == 0 for item in report["shells"]))

    @unittest.skipUnless(sys.platform.startswith("linux") and shutil.which("sh"), "Linux /bin/sh required")
    def test_extracted_install_and_rollback_parse_and_execute_preamble(self):
        self.git("config", "core.autocrlf", "true")
        output = Path(self.temporary.name) / "linux-shells.tar.gz"
        build(self.root, output)
        extracted = self.extract_and_check(output)
        tools = extracted / "tools"
        tools.mkdir()
        fake_id = tools / "id"
        fake_id.write_bytes(b"#!/bin/sh\nprintf '1000\\n'\n")
        fake_id.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(tools) + os.pathsep + env["PATH"]
        for name in self.scripts:
            with self.subTest(script=name):
                path = extracted / name
                syntax = subprocess.run(["sh", "-n", str(path)], capture_output=True)
                self.assertEqual(syntax.returncode, 0, syntax.stderr)
                # No root operations: both actual scripts stop at the explicit
                # UID guard. This executes set -eu, which sh -n alone does not.
                executed = subprocess.run(["sh", str(path)], env=env, capture_output=True)
                self.assertEqual(executed.returncode, 2)
                self.assertNotIn(b"Illegal option", executed.stderr)
                expected = b"Run as root on Camrui\n" if "install" in name else b""
                self.assertEqual(executed.stderr, expected)

    @unittest.skipUnless(sys.platform.startswith("linux") and shutil.which("sh"), "Linux /bin/sh required")
    def test_predecessor_windows_package_reproduces_reported_error(self):
        old_builder = (Path(__file__).resolve().parents[1] / "docs/history/RV-M1.1-002/rev1.0.0"
                       / "scripts/build_camrui_package.py")
        spec = importlib.util.spec_from_file_location("predecessor_builder", old_builder)
        predecessor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(predecessor)
        self.git("config", "core.autocrlf", "true")
        output = Path(self.temporary.name) / "predecessor-windows.tar.gz"
        predecessor.build(self.root, output)
        report, code = verify(output)
        self.assertEqual(code, 2)
        self.assertEqual(report["manifest"], "PASS")
        self.assertEqual(report["shell_compatibility"], "FAIL")
        self.assertTrue(all(item["line_15_hex"] == "736574202d65750d0a" for item in report["shells"]))
        with tarfile.open(output) as package:
            for name in self.scripts:
                data = package.extractfile(name).read()
                self.assertEqual(data, self.contents[name].replace(b"\n", b"\r\n"))
                line = data.splitlines(keepends=True)[14]
                self.assertEqual(line, b"set -eu\r\n")
                # Execute only the failed line; never deploy the historical file.
                result = subprocess.run(["sh", "-c", line.decode()], capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn(b"set: Illegal option -", result.stderr)

    def test_committed_invalid_shell_bytes_fail_before_archive_creation(self):
        name = self.scripts[0]
        content = self.contents[name]
        for label, invalid in [("CRLF", content.replace(b"\n", b"\r\n")),
                               ("BOM", b"\xef\xbb\xbf" + content),
                               ("NUL", content + b"\x00\n"),
                               ("no-final-LF", content.rstrip(b"\n"))]:
            with self.subTest(case=label):
                (self.root / name).write_bytes(invalid)
                self.git("add", name)
                self.git("commit", "-qm", label)
                output = Path(self.temporary.name) / (label + ".tar.gz")
                with self.assertRaisesRegex(ValueError, "Linux shell requires"):
                    build(self.root, output)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

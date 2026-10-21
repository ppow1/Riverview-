# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_runtime_baseline.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.11
# Purpose: Identity/credential security, DB contract, observer and package regression tests
# Execution Model: Request-driven tests; simulated DB explicitly distinct from live proof
# Observability: unittest counts and failures
# Dependencies: Python 3.10+, Git, Linux
# Authority: Temporary fixtures only; no live DB or credentials
# Changed: 2026-10-13 UTC | RV-M1.1-PACKAGE-BASH-001 | Cover allowlisted Bash packaging and safe runner behavior
# Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PACKAGING | Ensure tracked predecessor archives never enter release packages
# Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Guard full Camrui packages include the Grace exchange initiation and policy migration components.
# Changed: 2026-10-19 UTC | RV-W3-INTEGRATED-RELEASE-BLOCKER-RESOLUTION | Require byte-identical full-source archives for the same clean commit.
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: This file
# History: docs/history/RV-M1.1-002/rev1.0.0/tests/test_runtime_baseline.py
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
import pty
import secrets
import select
import stat
from pathlib import Path
import subprocess
import sys
import time
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
from provision_pgpass import pgpass_line, read_existing_password
from read_baseline_report import read_report
from verify_camrui_package import verify


class RuntimeBaselineTests(unittest.TestCase):
    def run_probe(self, rows=None, failure=None, identity=None, environ=None, passfile=None):
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
             patch.object(baseline, "systemd_credential_path"), \
             patch.object(baseline, "copy_systemd_credential"), \
             patch.dict(os.environ, environ or {}, clear=True):
            report, code = baseline.probe(passfile=passfile or Path("/run/riverview-credentials/pgpass"),
                                          credential_source=Path("/run/credentials/riverview-baseline.service/pgpass"),
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
        self.assertIn("host(inet_server_addr())", cur.execute.call_args_list[1].args[0])

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
            with self.assertRaises(baseline.BaselineError) as caught:
                baseline.private_path(link, os.getuid())
            self.assertEqual(caught.exception.detail, "symlink_in_path")
            path.write_text("")
            with self.assertRaises(baseline.BaselineError):
                baseline.private_path(path, os.getuid())

    def test_unsafe_path_reports_exact_safe_predicate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file_path = root / "not-a-directory"
            file_path.write_text("fixture")
            with self.assertRaises(baseline.BaselineError) as caught:
                baseline.private_path(file_path, os.getuid(), directory=True)
            self.assertEqual(caught.exception.detail, "unexpected_file_type")
            directory = root / "state"
            directory.mkdir(mode=0o700)
            with self.assertRaises(baseline.BaselineError) as caught:
                baseline.private_path(directory, os.getuid() + 1, directory=True)
            self.assertEqual(caught.exception.detail, "owner_uid_mismatch")

    def test_installed_unit_storage_contract_matches_runtime_default(self):
        repo = Path(__file__).resolve().parents[1]
        unit = (repo / "deploy/systemd/riverview-baseline.service").read_text()
        self.assertIn("User=riverview\n", unit)
        self.assertIn("Group=riverview\n", unit)
        self.assertIn("StateDirectory=riverview\n", unit)
        self.assertIn("StateDirectoryMode=0700\n", unit)
        self.assertIn("RuntimeDirectory=riverview-credentials\n", unit)
        self.assertIn("RuntimeDirectoryMode=0700\n", unit)
        self.assertIn("--passfile /run/riverview-credentials/pgpass", unit)
        self.assertNotIn("DynamicUser=yes", unit)
        self.assertIn('default=Path("/var/lib/riverview")',
                      (repo / "scripts/runtime_baseline.py").read_text())
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "riverview"
            state.mkdir(mode=0o700)
            baseline.private_path(state, os.getuid(), directory=True)

    def test_systemd_root_owned_credential_mount_is_accepted_without_relaxing_state_paths(self):
        expected_dir = Path("/run/credentials/riverview-baseline.service")
        expected_file = expected_dir / "pgpass"
        dir_stat = SimpleNamespace(st_mode=stat.S_IFDIR | 0o550, st_uid=0)
        file_stat = SimpleNamespace(st_mode=stat.S_IFREG | 0o440, st_uid=0, st_size=16)
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(expected_dir)}), \
             patch.object(Path, "lstat", autospec=True,
                          side_effect=lambda p: dir_stat if p == expected_dir else file_stat), \
             patch.object(Path, "resolve", autospec=True, side_effect=lambda p, **kw: p.absolute()), \
             patch.object(baseline.os, "access", return_value=True):
            baseline.systemd_credential_path(expected_file)

    def test_systemd_credential_delivery_rejects_wrong_directory_and_user_writable_file(self):
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": "/tmp/user-controlled"}):
            with self.assertRaisesRegex(baseline.BaselineError, "unexpected_credential_location"):
                baseline.systemd_credential_path(Path("/tmp/user-controlled/pgpass"))

    def test_systemd_credential_validator_accepts_only_requested_processor_unit(self):
        expected_dir = Path("/run/credentials/riverview-event-processor.service")
        expected_file = expected_dir / "pgpass"
        dir_stat = SimpleNamespace(st_mode=stat.S_IFDIR | 0o550, st_uid=0)
        file_stat = SimpleNamespace(st_mode=stat.S_IFREG | 0o440, st_uid=0, st_size=16)
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(expected_dir)}), \
             patch.object(Path, "lstat", autospec=True,
                          side_effect=lambda p: dir_stat if p == expected_dir else file_stat), \
             patch.object(Path, "resolve", autospec=True, side_effect=lambda p, **kw: p.absolute()), \
             patch.object(baseline.os, "access", return_value=True):
            baseline.systemd_credential_path(
                expected_file, service_unit="riverview-event-processor.service")
            with self.assertRaisesRegex(baseline.BaselineError, "unexpected_credential_location"):
                baseline.systemd_credential_path(
                    expected_file, service_unit="riverview-baseline.service")

    def test_probe_rejects_noncontract_runtime_passfile_location(self):
        report, code, connect, _ = self.run_probe(passfile=Path("/tmp/pgpass"))
        self.assertEqual(code, 2)
        self.assertEqual(report["blocker_code"], "UNSAFE_PATH")
        self.assertEqual(report["path_failure_reason"], "unexpected_runtime_credential_location")
        connect.assert_not_called()

    def test_root_owned_systemd_credential_is_copied_to_exclusive_private_libpq_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "credential-source"
            source.write_bytes(b"secret-fixture-never-reported")
            source.chmod(0o440)
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            destination = runtime / "pgpass"
            fake_info = SimpleNamespace(st_mode=stat.S_IFREG | 0o440, st_uid=0, st_size=29)
            with patch.object(baseline.os, "fstat", return_value=fake_info):
                baseline.copy_systemd_credential(source, destination, os.getuid())
            self.assertEqual(destination.read_bytes(), b"secret-fixture-never-reported")
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual(destination.stat().st_uid, os.getuid())
            with patch.object(baseline.os, "fstat", return_value=fake_info), \
                 self.assertRaises(baseline.BaselineError):
                baseline.copy_systemd_credential(source, destination, os.getuid())
            self.assertEqual(destination.read_bytes(), b"secret-fixture-never-reported")
            link = runtime / "linked"
            link.symlink_to(destination)
            with patch.object(baseline.os, "fstat", return_value=fake_info), \
                 self.assertRaises(baseline.BaselineError):
                baseline.copy_systemd_credential(source, link, os.getuid())

    def test_storage_path_failure_reports_reason_and_keeps_blocker_code(self):
        identity = SimpleNamespace(pw_uid=12345, pw_shell="/usr/sbin/nologin")
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "state"
            state.mkdir(mode=0o700)
            with patch.object(baseline.pwd, "getpwnam", return_value=identity), \
                 patch.object(baseline.os, "geteuid", return_value=12345), \
                 patch.dict(os.environ, {}, clear=True):
                report, code = baseline.probe(passfile=None, state_dir=state, connect=MagicMock())
        self.assertEqual(code, 2)
        self.assertEqual(report["step_id"], "storage")
        self.assertEqual(report["blocker_code"], "UNSAFE_PATH")
        self.assertEqual(report["path_failure_reason"], "owner_uid_mismatch")

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
            backup = root / ".riverview-backups" / "old" / "code.py"
            backup.parent.mkdir(parents=True)
            backup.write_text("predecessor must stay out of release\n")
            (root / "untracked-secret").write_text("NEVER_PACKAGE")
            subprocess.run(["git", "-C", str(root), "add", "code.py", ".riverview-backups"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
            output = Path(folder) / "package.tar.gz"
            commit, digest = build(root, output)
            self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())
            repeated_output = Path(folder) / "package-repeated.tar.gz"
            repeated_commit, repeated_digest = build(root, repeated_output)
            self.assertEqual(repeated_commit, commit)
            self.assertEqual(repeated_digest, digest)
            self.assertEqual(repeated_output.read_bytes(), output.read_bytes())
            with tarfile.open(output) as archive:
                self.assertNotIn("untracked-secret", archive.getnames())
                self.assertFalse(any(name.startswith(".riverview-backups/")
                                     for name in archive.getnames()))
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

    def test_full_camrui_package_includes_grace_exchange_and_comms5_policy_components(self):
        root_repo = Path(__file__).resolve().parents[1]
        required = (
            "scripts/run_grace_execution_service.py",
            "src/riverview_core/resident_reasoning.py",
            "src/riverview_core/local_reasoning_provider.py",
            "src/riverview_core/reasoning_escalation.py",
            "src/riverview_core/resident_execution/service.py",
            "src/riverview_core/resident_execution/external_reasoning.py",
            "src/riverview_core/resident_execution/migrations/0011_external_reasoning_exchange.sql",
            "src/riverview_core/resident_execution/migrations/0012_resource_selection_policy.sql",
        )
        with tempfile.TemporaryDirectory() as folder:
            isolated = Path(folder) / "repo"
            isolated.mkdir()
            subprocess.run(["git", "init", "-q", str(isolated)], check=True)
            for rel in required:
                target = isolated / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((root_repo / rel).read_bytes())
            subprocess.run(["git", "-C", str(isolated), "add", *required], check=True)
            subprocess.run(["git", "-C", str(isolated), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "-qm",
                            "package components"], check=True)
            package_path = Path(folder) / "grace-camrui.tar.gz"
            _commit, digest = build(isolated, package_path)
            self.assertEqual(digest, hashlib.sha256(package_path.read_bytes()).hexdigest())
            with tarfile.open(package_path, "r:gz") as archive:
                names = set(archive.getnames())
                self.assertTrue(set(required) <= names)
                manifest = archive.extractfile("PACKAGE_SHA256SUMS").read().decode().splitlines()
                for line in manifest:
                    checksum, name = line.split("  ", 1)
                    self.assertEqual(checksum,
                        hashlib.sha256(archive.extractfile(name).read()).hexdigest())



class CredentialTerminalTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux") and hasattr(pty, "fork"),
                         "Linux controlling pseudo-terminal required")
    def test_password_prompt_reads_nonseekable_tty_without_echo(self):
        expected = secrets.token_urlsafe(24)
        pid, master = pty.fork()
        if pid == 0:
            try:
                supplied = read_existing_password()
                marker = b"RV_PROMPT_MATCH\n" if supplied == expected else b"RV_PROMPT_MISMATCH\n"
                os.write(1, marker)
                os._exit(0)
            except BaseException:
                os.write(2, b"RV_PROMPT_ERROR\n")
                os._exit(1)

        output = bytearray()
        deadline = time.monotonic() + 8
        sent = False
        status = None
        try:
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], 0.2)
                if ready:
                    try:
                        output.extend(os.read(master, 4096))
                    except OSError:
                        break
                if not sent and b"Existing riverview_core database password" in output:
                    os.write(master, expected.encode() + b"\n")
                    sent = True
                if b"RV_PROMPT_MATCH\n" in output or b"RV_PROMPT_MISMATCH\n" in output or b"RV_PROMPT_ERROR\n" in output:
                    break
            self.assertTrue(sent, "prompt was not displayed on the controlling terminal")
            normalized = output.replace(b"\r\n", b"\n")
            self.assertIn(b"RV_PROMPT_MATCH\n", normalized)
            self.assertNotIn(expected.encode(), output, "terminal echoed the generated test secret")
            _, status = os.waitpid(pid, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        finally:
            if status is None:
                try:
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
            os.close(master)

    def test_installer_reuses_only_root_owned_directory_and_restores_read_access(self):
        project = Path(__file__).resolve().parents[1]
        script = (project / "deploy/install_baseline.sh").read_text()
        self.assertIn('[ -d "$release" ] && [ ! -L "$release" ]', script)
        self.assertIn('find "$release" ! -user root -print -quit', script)
        self.assertIn('chmod -R a+rX "$release"', script)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "release"
            nested = root / "scripts"
            nested.mkdir(parents=True)
            (nested / "runtime.py").write_text("pass\n")
            root.chmod(0o700)
            nested.chmod(0o700)
            subprocess.run(["chmod", "-R", "a+rX", str(root)], check=True)
            subprocess.run(["chmod", "-R", "go-w", str(root)], check=True)
            self.assertEqual(root.stat().st_mode & 0o777, 0o755)
            self.assertEqual(nested.stat().st_mode & 0o777, 0o755)
            self.assertEqual((nested / "runtime.py").stat().st_mode & 0o777, 0o644)


class InstallerQualificationTests(unittest.TestCase):
    def test_installer_uses_separate_pinned_environment_and_unprivileged_pytest(self):
        project = Path(__file__).resolve().parents[1]
        script = (project / "deploy/install_baseline.sh").read_text()
        requirements = (project / "deploy/qualification-requirements.txt").read_text()
        self.assertIn('install -d -o root -g root -m 0755 /opt/riverview/qualification', script)
        self.assertIn('python3 -m venv "$qualification_root/venv"', script)
        self.assertIn('pip install --disable-pip-version-check --no-deps --only-binary=:all: -r deploy/qualification-requirements.txt', script)
        self.assertIn('command -v runuser >/dev/null', script)
        self.assertIn('runuser -u riverview -- env', script)
        self.assertIn('pytest" -p no:cacheprovider -q tests', script)
        self.assertNotIn('python -m unittest discover -s tests', script)
        for dependency in ("PyJWT[crypto]==2.10.1", "jsonschema==4.23.0",
                           "pytest==8.3.5", "psycopg[binary]==3.2.10"):
            self.assertIn(dependency, requirements)


class PackageShellCompatibilityTests(unittest.TestCase):
    scripts = ("deploy/install_baseline.sh", "deploy/rollback_baseline.sh")
    supervised_script = "scripts/run_supervised_grace_execution.sh"

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
            for name in self.contents:
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

    def test_exact_supervised_bash_script_builds_verifies_and_runs_only_tty_guard(self):
        project = Path(__file__).resolve().parents[1]
        content = (project / self.supervised_script).read_bytes()
        self.assertIn(b"set -euo pipefail", content)
        self.assertIn(b"[[", content)
        self.assertIn(b"=~", content)
        path = self.root / self.supervised_script
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        self.contents[self.supervised_script] = content
        self.git("add", self.supervised_script)
        self.git("commit", "-qm", "Reviewed supervised Bash runner")

        output = Path(self.temporary.name) / "bash-runner.tar.gz"
        build(self.root, output)
        extracted = self.extract_and_check(output)
        packaged = extracted / self.supervised_script
        syntax = subprocess.run(["bash", "-n", str(packaged)], capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        report, code = verify(output)
        self.assertEqual(code, 0)
        self.assertEqual(report["shell_compatibility"], "PASS")
        bash_entry = next(item for item in report["shells"] if item["path"] == self.supervised_script)
        self.assertEqual(bash_entry["interpreter"], "bash")

        # Non-TTY execution exits before creating state or invoking sudo/systemd.
        execution = subprocess.run(["bash", str(packaged)], capture_output=True)
        self.assertEqual(execution.returncode, 2)
        self.assertIn(b"interactive terminal", execution.stderr)
        self.assertNotIn(b"systemd-run", execution.stderr)

    def test_unlisted_bash_script_and_malformed_allowlisted_script_fail_closed(self):
        from build_camrui_package import validate_shell
        content = b"#!/usr/bin/env bash\nset -euo pipefail\n"
        with self.assertRaisesRegex(ValueError, "POSIX /bin/sh"):
            validate_shell("scripts/other.sh", content)
        with self.assertRaisesRegex(ValueError, "authorized Bash"):
            validate_shell(self.supervised_script, content.replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(ValueError, "authorized Bash"):
            validate_shell(self.supervised_script, b"#!/bin/sh\nset -eu\n")


if __name__ == "__main__":
    unittest.main()

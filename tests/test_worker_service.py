# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_worker_service.py
# Component: WORKER-ADAPTER
# Revision: 1.1.3
# Changed: 2026-10-23 UTC | RV-COMFYUI-ROLLBACK-CAPABILITY | Cover exact capability removal and fail-closed registration mismatch handling.
# Changed: 2026-10-23 UTC | RV-COMFYUI-REGISTERED-CAPABILITY | Verify exact ComfyUI capability persistence across service restarts.
# Changed: 2026-10-23 UTC | RV-COMFYUI-REGISTERED-CAPABILITY | Cover grant-bound extension of an already registered Grace worker.
# Purpose: Enforce service identity, package paths, credentials and unit boundaries
# Execution Model: Local contract tests; PostgreSQL behavior is covered separately
# Observability: Safe configuration failure codes and reviewed unit properties
# Dependencies: Python standard library
# Authority: No credentials, shared database, or service process are used
# Changed: 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Initial service contract tests
# Changed: 2026-10-11 UTC | RV-M33-DEPLOYMENT-PATH-CORRECTION | Verify deployed runtime paths against Camrui layout
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Require shared private artifact state and custom verifier service contract
# Changed: 2026-10-11 UTC | RV-M33-ARTIFACT-TEST-CORRECTION | Assert imported capability definition rather than duplicated literal
# Changed: 2026-10-11 UTC | RV-M33-VERIFIER-PACKAGE-ROOT | Require verifier service package-root pin
# Changed: 2026-10-11 UTC | RV-M33-CREDENTIAL-NEWLINE | Cover the protected token file's single line terminator
# Changed: 2026-10-11 UTC | RV-M4.4-SERVICE-PATH-CONTRACT | Require Grace unit to use its own release and runner path
# Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Verify persistent owner-session unit stays bounded and no-copy
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-OWNER-STATE-001 | Assert isolated writable Codex state and read-only single-file auth bind
# Contracts: deploy/systemd/riverview-m33-worker.service; deploy/systemd/riverview-m33-verifier.service
# Tests: This file
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Local contract checks for separate, credentialed M3.3 worker units."""

from pathlib import Path
import hashlib
from contextlib import nullcontext
import unittest
from unittest.mock import Mock, patch

from riverview_core.worker_adapter.service import (
    WorkerServiceConfigurationError, _read_systemd_credential,
    _SERVICE_CREDENTIALS, _SERVICE_RUNTIME_USERS,
    configured_worker_capabilities, ensure_registered, read_worker_credential,
)


ROOT = Path(__file__).resolve().parents[1]


class WorkerServiceContractTests(unittest.TestCase):
    def test_comfyui_capability_is_stably_registered_only_when_enabled(self):
        self.assertEqual(
            configured_worker_capabilities("engineering.codex-cli-artifact.v1",
                                            comfyui_enabled=True),
            ("engineering.codex-cli-artifact.v1", "engineering.comfyui-image.v1"),
        )
        self.assertEqual(
            configured_worker_capabilities("engineering.codex-cli-artifact.v1",
                                            comfyui_enabled=False),
            ("engineering.codex-cli-artifact.v1",),
        )

    def test_existing_base_worker_adds_comfyui_only_through_registered_grant_operation(self):
        token = "t" * 64
        row = {
            "credential_sha256": hashlib.sha256(token.encode()).digest(),
            "capabilities": ["engineering.codex-cli-artifact.v1"],
            "scope_ref": "work-order:engineering",
            "active": True,
        }

        class Cursor:
            def execute(self, *_args):
                pass

            def fetchone(self):
                return row

        class Database:
            def transaction(self):
                return nullcontext()

            def cursor(self):
                return nullcontext(Cursor())

        class Ledger:
            db = Database()

            @staticmethod
            def _set_search_path(_cursor):
                pass

        class Adapter:
            COMFYUI_CAPABILITY = "engineering.comfyui-image.v1"
            ledger = Ledger()

            def __init__(self):
                self.register_comfyui_capability = Mock()
                self.register_worker = Mock()

        adapter = Adapter()
        ensure_registered(adapter, "worker:grace-engineering", token,
                          configured_worker_capabilities(
                              "engineering.codex-cli-artifact.v1", comfyui_enabled=True),
                          "work-order:engineering")
        adapter.register_comfyui_capability.assert_called_once_with(
            "worker:grace-engineering", token, "work-order:engineering")
        adapter.register_worker.assert_not_called()

    def test_rollback_removes_only_comfyui_through_registered_grant_operation(self):
        token = "t" * 64
        row = {
            "credential_sha256": hashlib.sha256(token.encode()).digest(),
            "capabilities": ["engineering.codex-cli-artifact.v1", "engineering.comfyui-image.v1"],
            "scope_ref": "work-order:engineering",
            "active": True,
        }

        class Cursor:
            def execute(self, *_args):
                pass

            def fetchone(self):
                return row

        class Database:
            def transaction(self):
                return nullcontext()

            def cursor(self):
                return nullcontext(Cursor())

        class Ledger:
            db = Database()

            @staticmethod
            def _set_search_path(_cursor):
                pass

        class Adapter:
            COMFYUI_CAPABILITY = "engineering.comfyui-image.v1"
            ledger = Ledger()

            def __init__(self):
                self.unregister_comfyui_capability = Mock()
                self.register_comfyui_capability = Mock()

        adapter = Adapter()
        ensure_registered(adapter, "worker:grace-engineering", token,
                          configured_worker_capabilities(
                              "engineering.codex-cli-artifact.v1", comfyui_enabled=False),
                          "work-order:engineering")
        adapter.unregister_comfyui_capability.assert_called_once_with(
            "worker:grace-engineering", token, "work-order:engineering")
        adapter.register_comfyui_capability.assert_not_called()

    def test_unexpected_registration_differences_still_fail_closed(self):
        token = "t" * 64
        row = {
            "credential_sha256": hashlib.sha256(token.encode()).digest(),
            "capabilities": ["engineering.codex-cli-artifact.v1", "engineering.comfyui-image.v1",
                             "engineering.unexpected.v1"],
            "scope_ref": "work-order:engineering",
            "active": True,
        }

        class Cursor:
            def execute(self, *_args):
                pass

            def fetchone(self):
                return row

        class Database:
            def transaction(self):
                return nullcontext()

            def cursor(self):
                return nullcontext(Cursor())

        class Ledger:
            db = Database()

            @staticmethod
            def _set_search_path(_cursor):
                pass

        class Adapter:
            COMFYUI_CAPABILITY = "engineering.comfyui-image.v1"
            ledger = Ledger()
            unregister_comfyui_capability = Mock()
            register_comfyui_capability = Mock()

        with self.assertRaises(WorkerServiceConfigurationError):
            ensure_registered(Adapter(), "worker:grace-engineering", token,
                              configured_worker_capabilities(
                                  "engineering.codex-cli-artifact.v1", comfyui_enabled=False),
                              "work-order:engineering")

    def test_grace_unit_points_to_its_own_release_and_runner(self):
        unit = (ROOT / "deploy/systemd/riverview-grace-execution.service").read_text()
        release = "/opt/riverview-grace-execution/current"
        self.assertIn(f"WorkingDirectory={release}", unit)
        self.assertIn(f"PYTHONPATH={release}/src:{release}/scripts", unit)
        self.assertIn(f"{release}/scripts/run_grace_execution_service.py", unit)
        self.assertIn(f"RIVERVIEW_KNOWLEDGE_ROOT={release}", unit)
        self.assertNotIn("/opt/riverview-m33/current", unit)

    def test_persistent_owner_session_unit_reuses_home_without_exposing_it_or_copying_auth(self):
        unit = (ROOT / "deploy/systemd/riverview-grace-execution-owner-session.service").read_text()
        self.assertIn("User=admin1", unit)
        self.assertIn("RIVERVIEW_CODEX_AUTH_MODE=chatgpt-owner-session", unit)
        self.assertIn("RIVERVIEW_ENGINEERING_ADAPTER=codex-cli", unit)
        self.assertIn("ProtectHome=tmpfs", unit)
        self.assertIn("RIVERVIEW_CODEX_HOME=/var/lib/riverview-grace-owner-session/codex-home", unit)
        self.assertIn("HOME=/var/lib/riverview-grace-owner-session", unit)
        self.assertIn("BindReadOnlyPaths=/home/admin1/.codex/auth.json:/var/lib/riverview-grace-owner-session/codex-home/auth.json", unit)
        self.assertNotIn("BindReadOnlyPaths=/home/admin1/.codex\n", unit)
        self.assertIn("LoadCredential=worker-token:/etc/riverview/worker/grace-executor.credential", unit)
        self.assertIn("LoadCredential=dashboard-token:/home/admin1/.config/riverview/status-dashboard.token", unit)
        self.assertIn("LoadCredential=verifier-token:/etc/riverview/worker/grace-verifier.credential", unit)
        self.assertIn("StateDirectoryMode=0700", unit)
        self.assertIn("NoNewPrivileges=yes", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertNotIn("CODEX_ACCESS_TOKEN", unit)
        self.assertNotIn("OPENAI_API_KEY", unit)
        self.assertNotIn("LoadCredential=codex", unit)

    def test_credential_reader_accepts_only_one_trailing_line_feed(self):
        token = "t" * 64
        with patch("riverview_core.worker_adapter.service._read_systemd_credential",
                   return_value=(token + "\n").encode("ascii")):
            self.assertEqual(read_worker_credential("riverview-m33-worker.service",
                                                    "worker-token"), token)
        for invalid in ((token + "\n\n").encode("ascii"),
                        (token + "\r\n").encode("ascii"), b"\xff"):
            with self.subTest(invalid=invalid[-2:]):
                with patch("riverview_core.worker_adapter.service._read_systemd_credential",
                           return_value=invalid):
                    with self.assertRaises(WorkerServiceConfigurationError):
                        read_worker_credential("riverview-m33-worker.service", "worker-token")

    def test_credential_loader_accepts_only_registered_service_units_and_names(self):
        for unit, name in (("unrelated.service", "pgpass"),
                           ("riverview-m33-worker.service", "unknown"),
                           ("riverview-m33-verifier.service", "worker-token")):
            with self.subTest(unit=unit, name=name):
                with self.assertRaises(WorkerServiceConfigurationError):
                    _read_systemd_credential(name, unit)

    def test_owner_session_unit_has_only_its_registered_protected_credentials(self):
        unit = "riverview-grace-execution-owner-session.service"
        self.assertEqual(_SERVICE_CREDENTIALS[unit], frozenset({
            "pgpass", "dispatch-token", "worker-token", "verifier-token", "resident-token"}))
        self.assertNotIn("worker-token", _SERVICE_CREDENTIALS["riverview-m33-verifier.service"])
        self.assertEqual(_SERVICE_RUNTIME_USERS[unit], "admin1")
        token = "R" * 48
        with patch("riverview_core.worker_adapter.service._read_systemd_credential",
                   return_value=token.encode("ascii")):
            self.assertEqual(read_worker_credential(unit, "resident-token"), token)

    def test_executor_and_verifier_have_separate_credentials_and_identities(self):
        worker = (ROOT / "deploy/systemd/riverview-m33-worker.service").read_text()
        verifier = (ROOT / "deploy/systemd/riverview-m33-verifier.service").read_text()
        self.assertIn("User=riverview", worker)
        self.assertIn("NoNewPrivileges=yes", worker)
        self.assertIn("LoadCredential=worker-token:/etc/riverview/worker/m33-worker.credential", worker)
        self.assertIn("LoadCredential=verifier-token:/etc/riverview/worker/m33-verifier.credential", verifier)
        self.assertIn("EnvironmentFile=/etc/riverview/m33-worker.env", worker)
        self.assertIn("EnvironmentFile=/etc/riverview/m33-verifier.env", verifier)
        self.assertIn("RepositoryContractTestAction", (ROOT / "scripts/run_worker_service.py").read_text())
        self.assertIn('CAPABILITY = "engineering.repository-check.v1"',
                      (ROOT / "src/riverview_core/worker_adapter/engineering_artifact.py").read_text())
        self.assertIn("RepositoryContractTestVerifier", (ROOT / "scripts/run_verifier_service.py").read_text())
        self.assertIn("RIVERVIEW_KNOWLEDGE_ROOT=/opt/riverview-m33/current", verifier)
        self.assertNotIn("PGPASSWORD", worker + verifier)

    def test_worker_service_unit_binds_to_expected_package_and_existing_database(self):
        for unit_path in (ROOT / "deploy/systemd/riverview-m33-worker.service",
                          ROOT / "deploy/systemd/riverview-m33-verifier.service"):
            unit = unit_path.read_text()
            self.assertIn("/opt/riverview-m33/current", unit)
            self.assertIn("ExecStart=/opt/riverview-core/.venv/bin/python", unit)
            self.assertNotIn("/opt/riverview-core/current", unit)
            self.assertIn("dbname=riverview user=riverview_core", unit)
            self.assertIn("ProtectSystem=strict", unit)
            self.assertIn("RuntimeDirectoryMode=0700", unit)
            self.assertIn("StateDirectory=riverview-m33-worker", unit)
            self.assertIn("StateDirectoryMode=0700", unit)
            self.assertIn("RIVERVIEW_ARTIFACT_DIR=/var/lib/riverview-m33-worker/artifacts", unit)
            self.assertIn("Restart=on-failure", unit)

    def test_intake_unit_uses_loopback_and_existing_runtime(self):
        unit = (ROOT / "deploy/systemd/riverview-assignment-intake.service").read_text()
        self.assertIn("RIVERVIEW_INTAKE_HOST=127.0.0.1", unit)
        self.assertIn("RIVERVIEW_INTAKE_PORT=8768", unit)
        self.assertIn("ExecStart=/opt/riverview-core/.venv/bin/python", unit)
        self.assertNotIn("/opt/riverview-core/current", unit)


if __name__ == "__main__":
    unittest.main()

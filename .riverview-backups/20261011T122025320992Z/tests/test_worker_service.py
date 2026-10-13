# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_worker_service.py
# Component: WORKER-ADAPTER
# Revision: 1.0.0
# Purpose: Enforce service identity, systemd credentials and unit boundaries
# Execution Model: Local contract tests; PostgreSQL behavior is covered separately
# Observability: Safe configuration failure codes and reviewed unit properties
# Dependencies: Python standard library
# Authority: No credentials, shared database, or service process are used
# Changed: 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Initial service contract tests
# Contracts: deploy/systemd/riverview-m33-worker.service; deploy/systemd/riverview-m33-verifier.service
# Tests: This file
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Local contract checks for separate, credentialed M3.3 worker units."""

from pathlib import Path
import unittest

from riverview_core.worker_adapter.service import (
    WorkerServiceConfigurationError, _read_systemd_credential,
)


ROOT = Path(__file__).resolve().parents[1]


class WorkerServiceContractTests(unittest.TestCase):
    def test_credential_loader_accepts_only_registered_service_units_and_names(self):
        for unit, name in (("unrelated.service", "pgpass"),
                           ("riverview-m33-worker.service", "unknown"),
                           ("riverview-m33-verifier.service", "worker-token")):
            with self.subTest(unit=unit, name=name):
                with self.assertRaises(WorkerServiceConfigurationError):
                    _read_systemd_credential(name, unit)

    def test_executor_and_verifier_have_separate_credentials_and_identities(self):
        worker = (ROOT / "deploy/systemd/riverview-m33-worker.service").read_text()
        verifier = (ROOT / "deploy/systemd/riverview-m33-verifier.service").read_text()
        self.assertIn("User=riverview", worker)
        self.assertIn("NoNewPrivileges=yes", worker)
        self.assertIn("LoadCredential=worker-token:/etc/riverview/worker/m33-worker.credential", worker)
        self.assertIn("LoadCredential=verifier-token:/etc/riverview/worker/m33-verifier.credential", verifier)
        self.assertIn("EnvironmentFile=/etc/riverview/m33-worker.env", worker)
        self.assertIn("EnvironmentFile=/etc/riverview/m33-verifier.env", verifier)
        self.assertIn("deterministic.sha256.v1", (ROOT / "scripts/run_worker_service.py").read_text())
        self.assertIn("assignment.verify.v1", (ROOT / "scripts/run_verifier_service.py").read_text())
        self.assertNotIn("PGPASSWORD", worker + verifier)

    def test_worker_service_unit_binds_to_expected_package_and_existing_database(self):
        for unit_path in (ROOT / "deploy/systemd/riverview-m33-worker.service",
                          ROOT / "deploy/systemd/riverview-m33-verifier.service"):
            unit = unit_path.read_text()
            self.assertIn("/opt/riverview-m33/current", unit)
            self.assertIn("dbname=riverview user=riverview_core", unit)
            self.assertIn("ProtectSystem=strict", unit)
            self.assertIn("Restart=on-failure", unit)


if __name__ == "__main__":
    unittest.main()

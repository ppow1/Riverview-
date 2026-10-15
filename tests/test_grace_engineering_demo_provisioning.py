# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_engineering_demo_provisioning.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.0
# Purpose: Verify fixed-scope provisioning and reversible owner-session unit staging
# Execution Model: Isolated filesystem and mocked authority interfaces; no production mutation
# Observability: Assert only fixed identities, actions, paths, modes, hashes and refusal codes
# Dependencies: Python standard library; provisioning and installer modules
# Authority: Never connects to PostgreSQL or systemd; no credentials are generated or read
# Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Add isolated provisioning and install rollback tests
# Contracts: docs/components/GRACE_ENGINEERING_DEMO_COMMISSIONING.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Safe, isolated contract tests for the bounded Grace demonstration provisioner."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import install_grace_owner_session as installer
from scripts import provision_grace_engineering_demo as provisioner


class ProvisioningContractTests(unittest.TestCase):
    def test_grant_plan_is_exact_and_separates_executor_from_verifier(self):
        self.assertEqual(provisioner.SCOPE, "work-order:engineering")
        grants = set(provisioner.GRANTS)
        self.assertIn(("steward:camrui", "objective.submit", "work-order:engineering",
                      "grace-demo:steward-objective-submit"), grants)
        self.assertIn(("resident:grace", "resident.conversation.send", "office:office:grace",
                      "grace-demo:resident-conversation-send"), grants)
        self.assertIn(("worker:grace-engineering", "assignment.execute", "work-order:engineering",
                      "grace-demo:executor-assignment-execute"), grants)
        self.assertIn(("verifier:grace-engineering", "assignment.verify", "work-order:engineering",
                      "grace-demo:verifier-assignment-verify"), grants)
        self.assertNotIn(("worker:grace-engineering", "assignment.verify", "work-order:engineering",
                          "grace-demo:verifier-assignment-verify"), grants)
        self.assertNotIn("codex.execute", {row[1] for row in provisioner.GRANTS})

    def test_cli_defaults_to_no_change(self):
        with mock.patch.object(provisioner.sys, "argv", ["provision_grace_engineering_demo.py"]):
            self.assertEqual(provisioner.main(), 0)

    def test_non_root_refusal_precedes_credentials_or_database(self):
        with mock.patch.object(provisioner.os, "geteuid", return_value=1000), \
             mock.patch.object(provisioner, "_validate_directories"), \
             self.assertRaisesRegex(provisioner.ProvisioningError, "root_local_operation_required"):
            provisioner.provision()

    def test_grant_id_collision_and_revoked_grant_fail_closed(self):
        class Cursor:
            def __init__(self, row): self.row = row
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, *_): pass
            def fetchone(self): return self.row
        class DB:
            def __init__(self, row): self.row = row
            def transaction(self): return mock.MagicMock()
            def cursor(self): return Cursor(self.row)
        class Registry:
            db = DB({"principal_id": "other", "action": "wrong", "scope_ref": "other", "revoked_at": None})
            def _path(self, _): pass
            def authorize(self, *_): raise provisioner.AuthorityDenied("missing")
            def grant(self, *_args, **_kwargs): raise AssertionError("must not grant on ID collision")
        with self.assertRaisesRegex(provisioner.ProvisioningError, "grant_id_collision"):
            provisioner._ensure_grant(Registry(), "steward", "credential", "p", "a", "s", "fixed")


class OwnerSessionInstallTests(unittest.TestCase):
    def test_template_pins_commit_and_rejects_unknown_identity(self):
        rendered = installer.render_environment(
            f"RIVERVIEW_KNOWLEDGE_COMMIT={installer.PLACEHOLDER}\n", "a" * 40)
        self.assertEqual(rendered, b"RIVERVIEW_KNOWLEDGE_COMMIT=" + b"a" * 40 + b"\n")
        with self.assertRaisesRegex(installer.InstallError, "source_commit_invalid"):
            installer.render_environment("x", "not-a-commit")

    def test_staged_files_are_reversible_and_digest_guarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unit = b"[Unit]\nDescription=test\n"
            env = b"SAFE=1\n"
            result = installer.stage_files(root, unit, env)
            self.assertEqual(hashlib.sha256((root / "etc/systemd/system" /
                installer.UNIT_NAME).read_bytes()).hexdigest(), result["unit_sha256"])
            with self.assertRaisesRegex(installer.InstallError, "rollback_digest_mismatch"):
                installer.restore_files(root, unit_sha256="0" * 64,
                                        environment_sha256=result["environment_sha256"])
            self.assertTrue((root / "etc/riverview/grace-execution.env").exists())
            self.assertTrue((root / "etc/systemd/system" / installer.UNIT_NAME).exists())
            restored = installer.restore_files(root, unit_sha256=result["unit_sha256"],
                environment_sha256=result["environment_sha256"])
            self.assertEqual(len(restored["removed"]), 2)
            self.assertFalse((root / "etc/riverview/grace-execution.env").exists())

    def test_existing_configuration_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "etc/systemd/system" / installer.UNIT_NAME
            target.parent.mkdir(parents=True)
            target.write_bytes(b"operator-owned\n")
            with self.assertRaisesRegex(installer.InstallError, "unit_destination_exists_requires_review"):
                installer.stage_files(root, b"new unit", b"new env")
            self.assertEqual(target.read_bytes(), b"operator-owned\n")

    def test_runtime_credential_path_matches_existing_secret_and_not_missing_directory(self):
        unit = (Path(__file__).resolve().parents[1] / installer.UNIT_SOURCE).read_text()
        runner = (Path(__file__).resolve().parents[1] / "scripts/run_supervised_grace_execution.sh").read_text()
        self.assertIn("LoadCredential=resident-token:/etc/riverview/grace/resident.credential", unit)
        self.assertIn("LoadCredential=resident-token:/etc/riverview/grace/resident.credential", runner)
        self.assertNotIn("/etc/riverview/residents/grace-office.credential", unit + runner)


if __name__ == "__main__":
    unittest.main()

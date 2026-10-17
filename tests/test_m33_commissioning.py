# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_m33_commissioning.py
# Component: M33-COMMISSIONING
# Revision: 1.0.0
# Purpose: Check fixed grant scope and safe refusal behavior of the M3.3 credential tool
# Execution Model: Pure standard-library tests; never connects to the authority database
# Observability: Grant action/scope IDs and argument refusal codes only
# Dependencies: Python standard library
# Authority: No file, credential, database, or system service is changed
# Changed: 2026-10-11 UTC | RV-M33-GOVERNED-COMMISSIONING | Initial bounded provisioner tests
# Contracts: scripts/provision_m33_runtime_credentials.py
# Tests: This file
# History: New file; Git
# =============================================================================
"""Contract checks for exact-scope M3.3 provisioning and decommissioning."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from unittest import mock
import unittest

from scripts import provision_m33_runtime_credentials as commissioning


class M33CommissioningTests(unittest.TestCase):
    def test_generated_state_has_only_the_five_required_exact_grants(self):
        state = commissioning._new_state("a" * 40)
        self.assertEqual(state["record_schema"], "rv.m33-commissioning.v1")
        self.assertEqual(state["source_commit"], "a" * 40)
        self.assertRegex(state["scope_ref"], r"^work-order:m33-live-[0-9a-f]{16}$")
        self.assertEqual(set(state["grant_ids"]), {
            "assignment.create", "worker.register.executor", "assignment.execute",
            "worker.register.verifier", "assignment.verify",
        })
        expiry = datetime.fromisoformat(state["valid_until"])
        created = datetime.fromisoformat(state["created_at"])
        self.assertLessEqual(expiry-created, timedelta(hours=8, seconds=1))
        self.assertGreater(expiry, created)
        self.assertNotIn("credential", json.dumps(state).lower())

    def test_unprivileged_call_fails_before_filesystem_or_database_access(self):
        with mock.patch.object(commissioning.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(commissioning.CommissioningError,
                                        "root_local_operation_required"):
                commissioning.provision()

    def test_command_rejects_arbitrary_arguments_without_running_provisioner(self):
        output = io.StringIO()
        with mock.patch.object(commissioning.sys, "argv", ["provision_m33", "--anything"]), \
             mock.patch.object(commissioning, "provision", side_effect=AssertionError("must not run")), \
             redirect_stdout(output):
            self.assertEqual(commissioning.main(), 2)
        self.assertEqual(json.loads(output.getvalue())["failure_code"], "arguments_not_allowed")


if __name__ == "__main__":
    unittest.main()

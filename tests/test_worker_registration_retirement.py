# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_worker_registration_retirement.py
# Component: WORKER-ADAPTER / INSTITUTIONAL-AUTHORITY
# Revision: 1.0.1
# Purpose: Verify exact M33 worker retirement preconditions, atomic audit, and preservation
# Execution Model: Disposable PostgreSQL schemas plus mocked systemd status
# Observability: unittest results and append-only authority event assertions
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; Psycopg
# Authority: Creates and drops only unique rvtest_* schemas
# Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Initial retirement regression tests
# Changed: 2026-10-17 UTC | M33-0009-SYSTEMD-PARSER-FIX | Cover named systemd property parsing independent of output order
# Contracts: docs/components/WORKER_ADAPTER_COOKBOOK.md; docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Isolated tests for exact, Steward-authorized worker-registration retirement."""

import hashlib
import os
import secrets
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class WorkerRegistrationRetirementTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.institutional_authority import AuthorityRegistry
        from riverview_core.postgres_migrations import apply_migrations
        from riverview_core.worker_adapter.retirement import (EXPECTED_ACTIVE, GRACE_IDS,
            RUN_GRANTS, RUN_ID, SCOPE, SERVICE_UNITS, WORKER_IDS,
            retire_revoked_m33_registrations)

        self.psycopg, self.sql = psycopg, sql
        self.RUN_ID, self.SCOPE, self.WORKER_IDS = RUN_ID, SCOPE, WORKER_IDS
        self.GRACE_IDS, self.EXPECTED_ACTIVE = GRACE_IDS, EXPECTED_ACTIVE
        self.RUN_GRANTS = RUN_GRANTS
        self.SERVICE_UNITS = SERVICE_UNITS
        self.retire = retire_revoked_m33_registrations
        self.work_schema, self.auth_schema = "rvtest_" + uuid4().hex, "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.work_schema)))
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.auth_schema)))
        root = Path(__file__).resolve().parents[1] / "src/riverview_core"
        apply_migrations(DSN, schema=self.work_schema, migrations_dir=root / "migrations")
        apply_migrations(DSN, schema=self.work_schema,
                         migrations_dir=root / "assignment_scheduler/migrations")
        apply_migrations(DSN, schema=self.work_schema,
                         migrations_dir=root / "worker_adapter/migrations")
        apply_migrations(DSN, schema=self.auth_schema,
                         migrations_dir=root / "institutional_authority/migrations")
        self.registry = AuthorityRegistry(DSN, schema=self.auth_schema)
        self.steward = secrets.token_urlsafe(32)
        self.admin.execute(sql.SQL("""INSERT INTO {}.institutional_principals
            (principal_id,principal_kind) VALUES ('steward:camrui','steward')""").format(sql.Identifier(self.auth_schema)))
        self.admin.execute(sql.SQL("""INSERT INTO {}.principal_credentials
            (credential_id,principal_id,credential_sha256) VALUES (%s,'steward:camrui',%s)""").format(sql.Identifier(self.auth_schema)),
            (uuid4(), hashlib.sha256(self.steward.encode()).digest()))
        self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES ('steward-manage','steward:camrui','identity.manage','institution',
            'steward:camrui','test')""").format(sql.Identifier(self.auth_schema)))
        self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES ('steward-grant','steward:camrui','authority.grant','institution',
            'steward:camrui','test')""").format(sql.Identifier(self.auth_schema)))
        self.admin.execute(sql.SQL("""INSERT INTO {}.institutional_authority_events
            (event_id,event_type,actor_id,subject_id)
            VALUES (%s,'steward_bootstrapped','steward:camrui','steward:camrui')""").format(sql.Identifier(self.auth_schema)), (uuid4(),))
        self._seed_registry()

    def tearDown(self):
        from psycopg import sql
        self.registry.close()
        for schema in (self.work_schema, self.auth_schema):
            self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        self.admin.close()

    def _seed_registry(self):
        worker = self.sql.Identifier(self.work_schema)
        authority = self.sql.Identifier(self.auth_schema)
        ids = list(self.EXPECTED_ACTIVE)
        ids.extend(("worker:m31:executor:historic", "worker:m31:verifier:historic"))
        for worker_id in ids:
            active = worker_id in self.EXPECTED_ACTIVE
            scope = self.SCOPE if worker_id in self.WORKER_IDS else "work-order:engineering"
            self.admin.execute(self.sql.SQL("INSERT INTO {}.worker_registry(worker_id,credential_sha256,capabilities,scope_ref,active) VALUES (%s,%s,'[]'::jsonb,%s,%s)").format(worker),
                               (worker_id, hashlib.sha256(worker_id.encode()).digest(), scope, active))
        principals = [(worker_id, "worker") for worker_id in self.WORKER_IDS]
        principals += [(worker_id, "worker") for worker_id in self.GRACE_IDS]
        for principal, kind in principals:
            self.admin.execute(self.sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,%s)").format(authority), (principal, kind))
            self.admin.execute(self.sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256,revoked_at) VALUES (%s,%s,%s,clock_timestamp())").format(authority), (uuid4(), principal, hashlib.sha256((principal + "revoked").encode()).digest()))
        for grant_id, (principal_id, action) in self.RUN_GRANTS.items():
            self.admin.execute(self.sql.SQL("INSERT INTO {}.authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref,revoked_at) VALUES (%s,%s,%s,%s,'steward:camrui','test',clock_timestamp())").format(authority), (grant_id, principal_id, action, self.SCOPE))
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.assignments
            (id,state,owner,authority_ref,objective_ref,workflow_id,workflow_step,correlation_id,updated_at)
            VALUES ('m33-historical','blocked','worker:m33',%s,'objective:m33','rv:test','WAITING_FOR_EVIDENCE','corr:m33',clock_timestamp())""").format(worker), (self.SCOPE,))
        attempt_id = uuid4()
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.worker_attempts
            (attempt_id,assignment_id,worker_id,lease_generation,capability,idempotency_key,
             input_sha256,status,started_at,finished_at)
            VALUES (%s,'m33-historical',%s,1,'engineering.repository-check.v1',%s,%s,'succeeded',
                    clock_timestamp()-interval '1 minute',clock_timestamp())""").format(worker),
            (attempt_id, self.WORKER_IDS[0], "retire-test:" + attempt_id.hex, "a" * 64))
        self.admin.execute(self.sql.SQL("""INSERT INTO {}.worker_results
            (attempt_id,result,result_sha256) VALUES (%s,'{{"fixture":"preserve"}}'::jsonb,%s)""").format(worker),
            (attempt_id, "b" * 64))

    def _retire(self):
        with mock.patch("riverview_core.worker_adapter.retirement._verify_stopped_services",
                        return_value={unit: {"active_state": "inactive", "sub_state": "dead", "main_pid": "0"}
                                      for unit in self.SERVICE_UNITS}):
            return self.retire(self.registry, self.steward,
                               worker_schema=self.work_schema)

    def test_retires_only_exact_m33_rows_and_appends_steward_audit(self):
        before = self.admin.execute(self.sql.SQL("SELECT id,state,updated_at FROM {}.assignments").format(self.sql.Identifier(self.work_schema))).fetchall()
        attempts_before = self.admin.execute(self.sql.SQL("SELECT attempt_id,assignment_id,worker_id,status FROM {}.worker_attempts ORDER BY attempt_id").format(self.sql.Identifier(self.work_schema))).fetchall()
        results_before = self.admin.execute(self.sql.SQL("SELECT attempt_id,result_sha256,recorded_at FROM {}.worker_results ORDER BY attempt_id").format(self.sql.Identifier(self.work_schema))).fetchall()
        result = self._retire()
        self.assertEqual(result["status"], "RETIRED")
        self.assertEqual(result["active_workers"], 3)
        self.assertEqual(result["remaining_active_worker_ids"], sorted(self.GRACE_IDS))
        rows = self.admin.execute(self.sql.SQL("SELECT worker_id,active FROM {}.worker_registry ORDER BY worker_id").format(self.sql.Identifier(self.work_schema))).fetchall()
        active = {row[0] for row in rows if row[1]}
        self.assertEqual(active, set(self.GRACE_IDS))
        after = self.admin.execute(self.sql.SQL("SELECT id,state,updated_at FROM {}.assignments").format(self.sql.Identifier(self.work_schema))).fetchall()
        self.assertEqual(before, after)
        self.assertEqual(attempts_before, self.admin.execute(self.sql.SQL("SELECT attempt_id,assignment_id,worker_id,status FROM {}.worker_attempts ORDER BY attempt_id").format(self.sql.Identifier(self.work_schema))).fetchall())
        self.assertEqual(results_before, self.admin.execute(self.sql.SQL("SELECT attempt_id,result_sha256,recorded_at FROM {}.worker_results ORDER BY attempt_id").format(self.sql.Identifier(self.work_schema))).fetchall())
        audit = self.admin.execute(self.sql.SQL("SELECT subject_id,event_type,payload->>'commissioning_run_id' FROM {}.institutional_authority_events WHERE event_type='worker_registration_retired' ORDER BY subject_id").format(self.sql.Identifier(self.auth_schema))).fetchall()
        self.assertEqual(audit, [(worker_id, "worker_registration_retired", self.RUN_ID) for worker_id in sorted(self.WORKER_IDS)])

    def test_rejects_non_steward_or_invalid_steward_credential(self):
        with self.assertRaises(Exception):
            self.retire(self.registry, "x" * 40)
        service_token = self.registry.create_principal(self.steward, "service:not-steward", "service")
        self.registry.grant(self.steward, "service:not-steward", "identity.manage", "institution",
                            policy_ref="test")
        with mock.patch("riverview_core.worker_adapter.retirement._verify_stopped_services",
                        return_value={unit: {"active_state": "inactive", "sub_state": "dead", "main_pid": "0"}
                                      for unit in self.SERVICE_UNITS}):
            with self.assertRaisesRegex(Exception, "active Steward"):
                self.retire(self.registry, service_token, worker_schema=self.work_schema)

    def test_rejects_any_active_worker_authority_without_mutation(self):
        self.admin.execute(self.sql.SQL("UPDATE {}.authority_grants SET revoked_at=NULL WHERE grant_id='rv-m33:e92ec51590b34cd3:assignment-execute'").format(self.sql.Identifier(self.auth_schema)))
        with self.assertRaisesRegex(Exception, "commissioning_grants_not_exactly_revoked"):
            self._retire()
        self.assertEqual(self.admin.execute(self.sql.SQL("SELECT count(*) FROM {}.worker_registry WHERE active").format(self.sql.Identifier(self.work_schema))).fetchone()[0], 5)

    def test_rejects_any_unrevoked_worker_credential_without_mutation(self):
        self.admin.execute(self.sql.SQL("UPDATE {}.principal_credentials SET revoked_at=NULL WHERE principal_id=%s").format(self.sql.Identifier(self.auth_schema)), (self.WORKER_IDS[0],))
        with self.assertRaisesRegex(Exception, "worker_credentials_not_revoked"):
            self._retire()
        self.assertEqual(self.admin.execute(self.sql.SQL("SELECT count(*) FROM {}.worker_registry WHERE active").format(self.sql.Identifier(self.work_schema))).fetchone()[0], 5)

    def test_rejects_active_lease_and_executable_assignment(self):
        with self.assertRaisesRegex(Exception, "executable_m33_assignment_exists"):
            self.admin.execute(self.sql.SQL("UPDATE {}.assignments SET state='ready' WHERE id='m33-historical'").format(self.sql.Identifier(self.work_schema)))
            self._retire()
        self.admin.execute(self.sql.SQL("UPDATE {}.assignments SET state='blocked' WHERE id='m33-historical'").format(self.sql.Identifier(self.work_schema)))
        self.admin.execute(self.sql.SQL("INSERT INTO {}.assignment_leases(assignment_id,worker_id,generation,acquired_at,heartbeat_at,expires_at) VALUES ('m33-historical',%s,1,clock_timestamp(),clock_timestamp(),clock_timestamp()+interval '1 hour')").format(self.sql.Identifier(self.work_schema)), (self.WORKER_IDS[0],))
        with self.assertRaisesRegex(Exception, "active_worker_lease_exists"):
            self._retire()


class ServiceStopGateTests(unittest.TestCase):
    def test_requires_every_exact_unit_stopped_with_pid_zero(self):
        from riverview_core.worker_adapter import retirement
        good = [mock.Mock(returncode=0, stdout="MainPID=0\nActiveState=inactive\nSubState=dead\n")
                for _ in retirement.SERVICE_UNITS]
        with mock.patch.object(retirement.subprocess, "run", side_effect=good):
            result = retirement._verify_stopped_services()
        self.assertEqual(set(result), set(retirement.SERVICE_UNITS))
        reordered = [mock.Mock(returncode=0, stdout="SubState=dead\nMainPID=0\nActiveState=inactive\n")
                     for _ in retirement.SERVICE_UNITS]
        with mock.patch.object(retirement.subprocess, "run", side_effect=reordered):
            result = retirement._verify_stopped_services()
        self.assertEqual({value["active_state"] for value in result.values()}, {"inactive"})
        bad = mock.Mock(returncode=0, stdout="MainPID=123\nActiveState=active\nSubState=running\n")
        with mock.patch.object(retirement.subprocess, "run", return_value=bad):
            with self.assertRaisesRegex(retirement.WorkerRetirementError, "m33_service_not_stopped"):
                retirement._verify_stopped_services()
        failed = mock.Mock(returncode=0, stdout="MainPID=0\nActiveState=failed\nSubState=failed\n")
        with mock.patch.object(retirement.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(retirement.WorkerRetirementError, "m33_service_not_stopped"):
                retirement._verify_stopped_services()
        malformed = mock.Mock(returncode=0, stdout="MainPID=0\nActiveState=inactive\nSubState=dead\nExtra=value\n")
        with mock.patch.object(retirement.subprocess, "run", return_value=malformed):
            with self.assertRaisesRegex(retirement.WorkerRetirementError, "m33_service_not_stopped"):
                retirement._verify_stopped_services()


if __name__ == "__main__":
    unittest.main()

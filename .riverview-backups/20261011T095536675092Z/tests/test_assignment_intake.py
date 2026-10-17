# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_assignment_intake.py
# Component: ASSIGNMENT-INTAKE
# Revision: 1.0.0
# Purpose: Verify exact Steward grants gate durable PostgreSQL assignment creation
# Execution Model: Isolated PostgreSQL schema and exact-grant SQL function
# Observability: Assignment/event rows, actor attribution, denial and idempotency
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL superuser test database; Psycopg 3
# Authority: Random rvtest schema only; no shared assignment or grant state
# Changed: 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE | Test exact-scope assignment.create enforcement
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md; docs/development/M3.3-001_REVISION_RECORD.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Isolated PostgreSQL integration tests for grant-gated assignment creation."""

import hashlib
import os
import secrets
import unittest
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class AuthorizedAssignmentIntakeTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from riverview_core.institutional_authority import ExactGrantAuthorizer
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations
        from riverview_core.assignment_intake import AuthorizedAssignmentIntake

        self.psycopg = psycopg
        self.sql = sql
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.ledger = None
        try:
            identity = self.admin.execute(
                "SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()
            if not identity or not identity["rolsuper"]:
                self.skipTest("isolated test DSN requires CREATE SCHEMA privileges")
            self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
            core = Path(__file__).resolve().parents[1] / "src/riverview_core"
            apply_migrations(DSN, schema=self.schema)
            apply_migrations(DSN, schema=self.schema,
                             migrations_dir=core / "institutional_authority/migrations")

            self.actor_id = "steward:m33-intake-test"
            self.scope = "work-order:test-project"
            self.credential = secrets.token_urlsafe(32)
            self.admin.execute(
                sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,'steward')")
                .format(sql.Identifier(self.schema)), (self.actor_id,))
            self.admin.execute(
                sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)")
                .format(sql.Identifier(self.schema)),
                (uuid4(), self.actor_id, hashlib.sha256(self.credential.encode()).digest()))
            self.admin.execute(sql.SQL("""INSERT INTO {}.authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                VALUES ('m33-assignment-create','{}','assignment.create',%s,'{}',
                        'rv.policy:test-assignment-intake.v1')""").format(
                            sql.Identifier(self.schema), sql.Literal(self.actor_id),
                            sql.Literal(self.actor_id)), (self.scope,))
            self.ledger = PostgresLedger(DSN, schema=self.schema)
            self.intake = AuthorizedAssignmentIntake(
                self.ledger, ExactGrantAuthorizer(self.schema))
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        if getattr(self, "ledger", None) is not None:
            self.ledger.close()
            self.ledger = None
        if getattr(self, "admin", None) is not None:
            if getattr(self, "schema", None):
                self.admin.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    self.sql.Identifier(self.schema)))
            self.admin.close()

    def test_exact_grant_creates_attributed_assignment_and_idempotent_event(self):
        assignment = self.intake.create(
            "m33-authorized-assignment", "engineering",
            "m33-create-authorized-assignment", credential=self.credential,
            authority_ref=self.scope, objective_ref="objective:authorized-test",
            contract_ref="rv.assignment-intake.test.v1",
            workflow_id="assignment-intake.test.v1")
        replay = self.intake.create(
            "m33-authorized-assignment", "engineering",
            "m33-create-authorized-assignment", credential=self.credential,
            authority_ref=self.scope, objective_ref="objective:authorized-test",
            contract_ref="rv.assignment-intake.test.v1",
            workflow_id="assignment-intake.test.v1")

        self.assertEqual(assignment["state"], "queued")
        self.assertEqual(replay["id"], assignment["id"])
        self.assertEqual(assignment["authority_ref"], self.scope)
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT actor_id,event_type FROM events WHERE assignment_id=%s",
                        (assignment["id"],))
            events = cur.fetchall()
        self.assertEqual(events, [{"actor_id": self.actor_id,
                                   "event_type": "assignment.created"}])

    def test_missing_wrong_scope_and_revoked_grants_fail_closed_without_rows(self):
        from riverview_core.assignment_intake import AssignmentIntakeDenied

        with self.assertRaises(AssignmentIntakeDenied):
            self.intake.create("m33-denied-missing", "engineering", "denied-missing",
                               credential=secrets.token_urlsafe(32),
                               authority_ref=self.scope, objective_ref="objective:denied")
        with self.assertRaises(AssignmentIntakeDenied):
            self.intake.create("m33-denied-scope", "engineering", "denied-scope",
                               credential=self.credential,
                               authority_ref="work-order:other-project",
                               objective_ref="objective:denied")

        self.admin.execute(self.sql.SQL("UPDATE {}.authority_grants SET revoked_at=clock_timestamp() WHERE grant_id='m33-assignment-create'")
                           .format(self.sql.Identifier(self.schema)))
        with self.assertRaises(AssignmentIntakeDenied):
            self.intake.create("m33-denied-revoked", "engineering", "denied-revoked",
                               credential=self.credential, authority_ref=self.scope,
                               objective_ref="objective:denied")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT count(*) AS n FROM assignments")
            self.assertEqual(cur.fetchone()["n"], 0)

    def test_authority_unavailable_fails_closed(self):
        from riverview_core.assignment_intake import (
            AssignmentIntakeUnavailable, AuthorizedAssignmentIntake,
        )
        from riverview_core.institutional_authority import GrantCheckUnavailable

        class Unavailable:
            def require(self, *args):
                raise GrantCheckUnavailable("private diagnostic detail")

        intake = AuthorizedAssignmentIntake(self.ledger, Unavailable())
        with self.assertRaises(AssignmentIntakeUnavailable):
            intake.create("m33-denied-unavailable", "engineering", "denied-unavailable",
                          credential=self.credential, authority_ref=self.scope,
                          objective_ref="objective:denied")
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT count(*) AS n FROM assignments")
            self.assertEqual(cur.fetchone()["n"], 0)

    def test_request_cannot_choose_a_different_actor(self):
        with self.assertRaises(TypeError):
            self.intake.create("m33-forged-actor", "engineering", "forged-actor",
                               credential=self.credential, authority_ref=self.scope,
                               objective_ref="objective:denied", actor_id="steward:forged")

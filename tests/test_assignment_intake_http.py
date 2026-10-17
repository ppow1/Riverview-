# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_assignment_intake_http.py
# Component: ASSIGNMENT-INTAKE
# Revision: 1.0.0
# Purpose: Verify loopback request path enforces exact grants before persistence
# Execution Model: HTTP integration against a unique isolated PostgreSQL schema
# Observability: HTTP decisions, assignment attribution, and event count
# Dependencies: Python standard library; Psycopg 3; disposable PostgreSQL test database
# Authority: Never targets shared Riverview schemas or credentials
# Changed: 2026-10-11 UTC | RV-M3.3-GOVERNED-INTAKE-ROUTE | Initial route tests
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: This file
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""End-to-end HTTP tests for grant-gated assignment creation."""

import hashlib
import json
import os
import secrets
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


class AssignmentIntakeHTTPBoundaryTests(unittest.TestCase):
    def test_listener_rejects_non_loopback_bind(self):
        from riverview_core.assignment_intake_http import AssignmentIntakeHTTPServer
        with self.assertRaises(ValueError):
            AssignmentIntakeHTTPServer(("0.0.0.0", 0), object, dsn="", schema="", authority_schema="")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class AssignmentIntakeHTTPPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from riverview_core.postgres_migrations import apply_migrations
        from riverview_core.assignment_intake_http import (
            AssignmentIntakeHandler, AssignmentIntakeHTTPServer,
        )

        self.psycopg, self.sql = psycopg, sql
        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        identity = self.admin.execute("SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()
        if not identity or not identity["rolsuper"]:
            self.admin.close()
            self.skipTest("isolated test DSN requires CREATE SCHEMA privileges")
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        core = Path(__file__).resolve().parents[1] / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=core / "institutional_authority/migrations")
        self.scope = "work-order:m33-http-test"
        self.actor_id = "steward:m33-http-test"
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
            VALUES ('m33-http-create',%s,'assignment.create',%s,%s,
                    'rv.policy:m33-http-test.v1')""").format(sql.Identifier(self.schema)),
            (self.actor_id, self.scope, self.actor_id))
        self.server = AssignmentIntakeHTTPServer(
            ("127.0.0.1", 0), AssignmentIntakeHandler, dsn=DSN,
            schema=self.schema, authority_schema=self.schema)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        if getattr(self, "server", None) is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=3)
        if getattr(self, "admin", None) is not None:
            self.admin.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                self.sql.Identifier(self.schema)))
            self.admin.close()

    def post(self, path, payload, credential):
        request = Request(self.base + path,
                          data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json",
                                   "Authorization": "Bearer " + credential}, method="POST")
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_authorized_request_persists_and_unauthorized_request_has_no_effect(self):
        payload = {"assignment_id": "m33-http-authorized",
                   "owner": "engineering", "idempotency_key": "m33-http-authorized",
                   "authority_ref": self.scope,
                   "objective_ref": "objective:exercise-governed-assignment-intake",
                   "contract_ref": "rv.test.http.v1"}
        denied_status, denied = self.post(
            "/api/v1/assignments", dict(payload, assignment_id="m33-http-denied",
                                         idempotency_key="m33-http-denied"),
            secrets.token_urlsafe(32))
        self.assertEqual(denied_status, 403)
        self.assertEqual(denied["error"], "assignment_create_denied")

        status, created = self.post("/api/v1/assignments", payload, self.credential)
        self.assertEqual(status, 200)
        self.assertEqual(created["assignment"]["state"], "queued")
        replay_status, replay = self.post("/api/v1/assignments", payload, self.credential)
        self.assertEqual(replay_status, 200)
        self.assertEqual(replay["assignment"]["assignment_id"], "m33-http-authorized")

        invalid_status, invalid = self.post(
            "/api/v1/assignments", dict(payload, assignment_id="m33-http-forged",
                                         idempotency_key="m33-http-forged",
                                         actor_id="steward:forged"), self.credential)
        self.assertEqual(invalid_status, 400)
        self.assertEqual(invalid["error"], "request_invalid")
        rows = self.admin.execute(
            self.sql.SQL("SELECT id,actor_id FROM {}.assignments JOIN {}.events ON events.assignment_id=assignments.id WHERE assignments.id=%s")
            .format(self.sql.Identifier(self.schema), self.sql.Identifier(self.schema)),
            ("m33-http-authorized",)).fetchall()
        self.assertEqual(rows, [{"id": "m33-http-authorized", "actor_id": self.actor_id}])
        count = self.admin.execute(
            self.sql.SQL("SELECT count(*) AS n FROM {}.assignments").format(
                self.sql.Identifier(self.schema))).fetchone()["n"]
        self.assertEqual(count, 1)

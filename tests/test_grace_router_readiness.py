# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_router_readiness.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.2
# Purpose: Verify router startup readiness under restricted authority-ledger access
# Execution Model: Isolated PostgreSQL integration test
# Observability: Explicit migration, ledger-denial, authority, and binding assertions
# Dependencies: Psycopg 3; private RIVERVIEW_TEST_PG_DSN; dashboard readiness helper
# Authority: Creates and drops only unique rvtest_* schemas and a unique test role
# Changed: 2026-10-13 UTC | RV-GRACE-ROUTER-ACL-READINESS-001 | Add least-privilege startup regression coverage
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Require both deferred migrations and the runtime-only compatibility function at startup
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: python3 -m unittest tests.test_grace_router_readiness -v
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""ACL-faithful PostgreSQL regression tests for Grace router startup."""

import os
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


class _Router:
    provider_id = "grace.readiness_router.v1"
    model_sha256 = "a" * 64


class _Registry:
    def __init__(self, snapshot=None, error=None):
        self.snapshot = snapshot or {
            "implementation_id": "implementation:test-router",
            "implementation_kind": "model",
            "provider_ref": _Router.provider_id,
            "implementation_revision": _Router.model_sha256,
        }
        self.error = error
        self.calls = []
        self.compatibility_calls = []

    def authorize_office_state(self, credential, office_id):
        self.calls.append((credential, office_id))
        if self.error:
            raise self.error
        return self.snapshot

    def is_authorized_implementation_successor(self, credential, office_id, **kwargs):
        self.compatibility_calls.append((credential, office_id, kwargs))
        return False


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class GraceRouterReadinessPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql

        self.psycopg = psycopg
        self.sql = sql
        suffix = uuid4().hex
        self.app_schema = "rvtest_app_" + suffix
        self.authority_schema = "rvtest_auth_" + suffix
        self.runtime_role = "rvtest_runtime_" + suffix[:20]
        self.db = psycopg.connect(DSN, autocommit=True)
        identity = self.db.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()
        if not identity or not identity[0]:
            self.db.close()
            self.skipTest("isolated PostgreSQL DSN needs superuser role-boundary setup")
        self.db.execute(sql.SQL(
            "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
        ).format(sql.Identifier(self.runtime_role)))
        self.db.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION CURRENT_USER").format(
            sql.Identifier(self.app_schema)))
        self.db.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION CURRENT_USER").format(
            sql.Identifier(self.authority_schema)))
        for schema in (self.app_schema, self.authority_schema):
            self.db.execute(sql.SQL("""CREATE TABLE {}.schema_migrations(
                version text PRIMARY KEY, checksum text NOT NULL)""").format(
                sql.Identifier(schema)))
        self.db.execute(sql.SQL(
            "INSERT INTO {}.schema_migrations(version,checksum) VALUES (%s,%s)"
        ).format(sql.Identifier(self.app_schema)),
            ("0004_deferred_conversation_responses", "b" * 64))
        self.db.execute(sql.SQL(
            "INSERT INTO {}.schema_migrations(version,checksum) VALUES (%s,%s)"
        ).format(sql.Identifier(self.app_schema)),
            ("0006_deferred_execution_claims", "d" * 64))
        self.db.execute(sql.SQL(
            "INSERT INTO {}.schema_migrations(version,checksum) VALUES (%s,%s)"
        ).format(sql.Identifier(self.app_schema)),
            ("0008_resident_conversation_stream_delivery", "e" * 64))
        self.db.execute(sql.SQL("CREATE TABLE {}.resident_conversation_streams(id integer)").format(
            sql.Identifier(self.app_schema)))
        self.db.execute(sql.SQL(
            "INSERT INTO {}.schema_migrations(version,checksum) VALUES (%s,%s)"
        ).format(sql.Identifier(self.authority_schema)),
            ("0005_audited_model_rebinding", "c" * 64))
        for schema in (self.app_schema, self.authority_schema):
            self.db.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(self.runtime_role)))
        self.db.execute(sql.SQL("GRANT SELECT ON {}.schema_migrations TO {}").format(
            sql.Identifier(self.app_schema), sql.Identifier(self.runtime_role)))
        self.db.execute(sql.SQL(
            "GRANT SELECT,INSERT,UPDATE ON {}.resident_conversation_streams TO {}"
        ).format(sql.Identifier(self.app_schema), sql.Identifier(self.runtime_role)))
        self.db.execute(sql.SQL("REVOKE ALL ON {}.schema_migrations FROM {}").format(
            sql.Identifier(self.authority_schema), sql.Identifier(self.runtime_role)))

    def tearDown(self):
        if getattr(self, "db", None) is None or self.db.closed:
            return
        self.db.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
            self.sql.Identifier(self.app_schema)))
        self.db.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
            self.sql.Identifier(self.authority_schema)))
        self.db.execute(self.sql.SQL("DROP ROLE IF EXISTS {}").format(
            self.sql.Identifier(self.runtime_role)))
        self.db.close()

    def _run_as_runtime(self, registry):
        from riverview_core.status_dashboard.server import (
            _verify_grace_router_startup_readiness,
        )

        with self.db.transaction():
            self.db.execute(self.sql.SQL("SET LOCAL ROLE {}").format(
                self.sql.Identifier(self.runtime_role)))
            return _verify_grace_router_startup_readiness(
                self.db, schema=self.app_schema, registry=registry,
                resident_credential="test-resident-credential",
                office_id="office:test", router=_Router())

    def test_restricted_authority_ledger_does_not_block_valid_router(self):
        # Confirm visibility and denial with the actual temporary runtime role.
        with self.db.transaction():
            self.db.execute(self.sql.SQL("SET LOCAL ROLE {}").format(
                self.sql.Identifier(self.runtime_role)))
            visible = self.db.execute("""SELECT EXISTS(
                SELECT 1 FROM information_schema.tables
                 WHERE table_schema=%s AND table_name='schema_migrations')""",
                (self.authority_schema,)).fetchone()[0]
            self.assertFalse(visible)
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                with self.db.transaction():
                    self.db.execute(self.sql.SQL("SELECT version FROM {}.schema_migrations").format(
                        self.sql.Identifier(self.authority_schema)))
        registry = _Registry()
        result = self._run_as_runtime(registry)
        self.assertEqual(result["provider_ref"], _Router.provider_id)
        self.assertEqual(registry.calls, [("test-resident-credential", "office:test")])
        self.assertEqual(len(registry.compatibility_calls), 1)

    def test_missing_resident_migration_fails_closed(self):
        self.db.execute(self.sql.SQL("DELETE FROM {}.schema_migrations").format(
            self.sql.Identifier(self.app_schema)))
        with self.assertRaisesRegex(RuntimeError, "deferred-resumption migrations are not applied"):
            self._run_as_runtime(_Registry())

    def test_missing_claim_migration_fails_closed(self):
        self.db.execute(self.sql.SQL(
            "DELETE FROM {}.schema_migrations WHERE version=%s").format(
            self.sql.Identifier(self.app_schema)),
            ("0006_deferred_execution_claims",))
        with self.assertRaisesRegex(RuntimeError, "deferred-resumption migrations are not applied"):
            self._run_as_runtime(_Registry())

    def test_unavailable_authority_capability_fails_closed(self):
        registry = _Registry(error=RuntimeError("authority API unavailable"))
        with self.assertRaisesRegex(RuntimeError, "authority API unavailable"):
            self._run_as_runtime(registry)

    def test_router_binding_must_match_registered_provider_and_digest(self):
        registry = _Registry(snapshot={
            "implementation_kind": "model",
            "provider_ref": "local.inference.v1",
            "implementation_revision": "d" * 64,
        })
        with self.assertRaisesRegex(RuntimeError, "binding is not ready"):
            self._run_as_runtime(registry)

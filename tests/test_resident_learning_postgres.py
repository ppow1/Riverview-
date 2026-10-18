# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_learning_postgres.py
# Component: RESIDENT-LEARNING-GOVERNANCE
# Revision: 1.0.1
# Purpose: Verify append-only learning persistence and restart retrieval in isolated PostgreSQL
# Execution Model: Unique disposable schema; skipped unless RIVERVIEW_TEST_PG_DSN is set
# Observability: Persisted records, evidence, events, and authorization receipts
# Dependencies: PostgreSQL; Psycopg 3; RIVERVIEW_TEST_PG_DSN
# Authority: Synthetic test principals; unique disposable schema only
# Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-IMPLEMENTATION-001 | Add isolated PostgreSQL persistence test
# Changed: 2026-10-18 UTC | RV-W2-PR117-POSTGRES-001 | Verify scope filtering and database append-only triggers
# Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
import os
from pathlib import Path
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class ResidentLearningPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql

        self.psycopg, self.sql = psycopg, sql
        self.schema = "rvlearn_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        migration = ROOT / "src/riverview_core/resident_execution/migrations/0014_resident_learning.sql"
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            cur.execute(migration.read_text(encoding="utf-8"), prepare=False)

    def tearDown(self):
        if hasattr(self, "admin"):
            self.admin.execute(self.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                self.sql.Identifier(self.schema)))
            self.admin.close()

    def test_persist_and_resume_approved_shared_record(self):
        from riverview_core.resident_execution.resident_learning import (
            PostgresResidentLearningStore, ResidentLearningService)

        class Allow:
            def require(self, principal_id, operation, scope_ref):
                return {"principal_id": principal_id, "grant_id": "fixture:" + operation,
                        "authority_reference": "fixture-authority:" + operation}

        service = ResidentLearningService(PostgresResidentLearningStore(DSN, schema=self.schema), Allow())
        try:
            evidence = [{"source_ref":"fixture://source/1", "source_kind":"external_source",
                "captured_at":"2026-10-18T12:00:00Z", "source_revision":"v1",
                "source_sha256":"a" * 64}]
            candidate = service.create_candidate("resident:fixture", scope_ref="institution:riverview",
                content="fixture knowledge", evidence=evidence,
                provenance={"recorder_id":"resident:fixture", "method":"fixture",
                    "implementation_revision":"test", "interpretation":"imported_source"},
                classification="internal", retention="bounded_durable", idempotency_key="pg:create")
            validated = service.validate("resident:reviewer", candidate["record_id"],
                scope_ref="institution:riverview", expected_revision=1, result="SUPPORTED",
                evidence_refs=["fixture://review/1"], authority_event_ref="fixture:validation",
                idempotency_key="pg:validate")
            approved = service.approve_shared("steward:fixture", candidate["record_id"],
                expected_revision=validated["revision"], approved_purpose="isolated persistence test",
                authority_event_ref="fixture:steward", idempotency_key="pg:approve")
            service.store.close()

            resumed_store = PostgresResidentLearningStore(DSN, schema=self.schema)
            try:
                resumed = ResidentLearningService(resumed_store, Allow())
                result = resumed.retrieve("steward:fixture", scope_ref="institution:riverview")
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["record_id"], approved["record_id"])
                self.assertEqual(result[0]["evidence"][0]["source_sha256"], "a" * 64)
                self.assertEqual([e["event_type"] for e in result[0]["events"]],
                    ["candidate_created", "validated", "approved"])
                self.assertEqual(resumed.retrieve("resident:fixture",
                    scope_ref="resident:fixture"), [])

                identity = approved["record_id"].removeprefix("learning:")
                for table, assignment in (
                    ("resident_learning_records", "retention=retention"),
                    ("resident_learning_revisions", "content=content"),
                    ("resident_learning_events", "payload=payload"),
                ):
                    with self.subTest(table=table, operation="update"):
                        with self.assertRaises(self.psycopg.errors.ObjectNotInPrerequisiteState):
                            self.admin.execute(self.sql.SQL(
                                "UPDATE {}.{} SET " + assignment + " WHERE " +
                                ("record_id=%s" if table != "resident_learning_events" else "record_id=%s")
                            ).format(self.sql.Identifier(self.schema), self.sql.Identifier(table)),
                                (identity,))
                    with self.subTest(table=table, operation="delete"):
                        with self.assertRaises(self.psycopg.errors.ObjectNotInPrerequisiteState):
                            self.admin.execute(self.sql.SQL(
                                "DELETE FROM {}.{} WHERE record_id=%s"
                            ).format(self.sql.Identifier(self.schema), self.sql.Identifier(table)),
                                (identity,))
            finally:
                resumed_store.close()
        finally:
            if not service.store.db.closed:
                service.store.close()


if __name__ == "__main__":
    unittest.main()

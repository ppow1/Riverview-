"""Regression coverage for event-history identity access and least privilege."""

import hashlib
import os
import unittest
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
CORE = Path(__file__).resolve().parents[1] / "src/riverview_core"


class GraceEventHistoryMigrationContractTests(unittest.TestCase):
    def test_forward_migration_grants_only_event_id_select(self):
        migration = CORE / "resident_execution/migrations/0017_grace_objective_event_id_select.sql"
        source = migration.read_text(encoding="utf-8")
        self.assertRegex(source, r"GRANT\s+SELECT\s*\(event_id\)\s+ON")
        self.assertNotRegex(source, r"GRANT\s+SELECT\s+ON")
        self.assertNotRegex(source, r"GRANT\s+(?:UPDATE|DELETE|ALL)")
        self.assertEqual(len(hashlib.sha256(migration.read_bytes()).hexdigest()), 64)

    def test_event_history_query_includes_event_id(self):
        source = (CORE / "resident_execution/pipeline.py").read_text(encoding="utf-8")
        method = source.split("    def objective_events(", 1)[1].split("    def ", 1)[0]
        self.assertRegex(method, r"SELECT\s+event_id\s*,\s*event_type")
        self.assertRegex(method, r"FROM\s+grace_objective_events\s+WHERE\s+objective_id=%s\s+ORDER BY\s+sequence")

    def test_event_history_method_executes_exact_select_and_returns_identity(self):
        from riverview_core.resident_execution.pipeline import GraceExecutionPipeline

        class Cursor:
            def __init__(self):
                self.calls = []

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def execute(self, statement, params=()):
                self.calls.append((statement, params))

            def fetchall(self):
                return [{"event_id": "f8d9c2e3", "event_type": "objective.received"}]

        class DB:
            def __init__(self):
                self.cursor_value = Cursor()

            def cursor(self):
                return self.cursor_value

        class Ledger:
            def __init__(self):
                self.db = DB()

            @staticmethod
            def _set_search_path(cur):
                cur.execute("SET LOCAL search_path TO test_schema")

        ledger = Ledger()
        pipeline = GraceExecutionPipeline.__new__(GraceExecutionPipeline)
        pipeline.ledger = ledger
        rows = pipeline.objective_events("objective:test")
        statement, params = ledger.db.cursor_value.calls[-1]
        self.assertEqual(statement, """SELECT event_id,event_type,idempotency_key,actor_id,payload,occurred_at
                FROM grace_objective_events WHERE objective_id=%s ORDER BY sequence""")
        self.assertEqual(params, ("objective:test",))
        self.assertEqual(rows[0]["event_id"], "f8d9c2e3")

    def test_runtime_units_default_to_normal_and_collect_in_journal(self):
        root = Path(__file__).resolve().parents[1]
        dashboard = (root / "deploy/riverview-status-dashboard.service").read_text()
        owner = (root / "deploy/systemd/riverview-grace-execution-owner-session.service").read_text()
        for unit, diagnostics_file in ((dashboard, "dashboard-diagnostics.env"),
                                       (owner, "grace-diagnostics.env")):
            self.assertIn("Environment=RIVERVIEW_DIAGNOSTICS_MODE=NORMAL", unit)
            self.assertIn(diagnostics_file, unit)
            self.assertIn("StandardOutput=journal", unit)
            self.assertIn("StandardError=journal", unit)


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class GraceEventHistoryACLPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.postgres_migrations import apply_migrations

        self.psycopg = psycopg
        self.sql = sql
        self.schema = "rvtest_" + uuid4().hex
        self.db = psycopg.connect(DSN, autocommit=True)
        self.db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema,
                         migrations_dir=CORE / "resident_execution/migrations")
        migration = CORE / "resident_execution/migrations/0017_grace_objective_event_id_select.sql"
        checksum = hashlib.sha256(migration.read_bytes()).hexdigest()
        applied = self.db.execute("SELECT checksum FROM schema_migrations WHERE version=%s",
                                  ("0017_grace_objective_event_id_select",)).fetchone()
        self.assertEqual(applied[0], checksum)

    def tearDown(self):
        self.db.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(
            self.sql.Identifier(self.schema)))
        self.db.close()

    def test_event_id_select_is_granted_without_table_or_write_privileges(self):
        if not self.db.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)",
                               ("riverview_core",)).fetchone()[0]:
            self.skipTest("riverview_core role is absent in disposable PostgreSQL")
        qualified = f'{self.schema}.grace_objective_events'
        grants = self.db.execute("""SELECT
            has_column_privilege('riverview_core', %s, 'event_id', 'SELECT'),
            has_table_privilege('riverview_core', %s, 'SELECT'),
            has_table_privilege('riverview_core', %s, 'UPDATE'),
            has_table_privilege('riverview_core', %s, 'DELETE')""",
            (qualified, qualified, qualified, qualified)).fetchone()
        self.assertEqual(grants, (True, False, False, False))


if __name__ == "__main__":
    unittest.main()

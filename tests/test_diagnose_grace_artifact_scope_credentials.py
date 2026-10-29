from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import unittest
from unittest import mock
import psycopg
from psycopg.conninfo import conninfo_to_dict
from riverview_core.institutional_authority import AuthorityRegistry
from riverview_core.postgres_ledger import PostgresLedger

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "diagnose_grace_artifact_scope.py"
spec = importlib.util.spec_from_file_location("scope_diagnostic", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class _Cursor:
    def __init__(self):
        self.query = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, _params=None):
        self.query = str(query)

    def fetchone(self):
        if "EXISTS" in self.query:
            return {"present": True}
        if "to_regclass" in self.query:
            return {"ledger": "schema_migrations"}
        if "SELECT version" in self.query:
            return {"version": "test-migration"}
        return None


class _Connection:
    def cursor(self):
        return _Cursor()

    def close(self):
        pass


class PgpassInMemoryConnectionTests(unittest.TestCase):
    def test_systemd_0440_entry_becomes_readonly_conninfo_without_passfile(self):
        before = os.environ.get("PGPASSFILE")
        dsn = module._readonly_dsn(b"127.0.0.1:5432:riverview:riverview_core:sample\\:secret\\\\value\n")
        parsed = conninfo_to_dict(dsn)
        self.assertEqual(parsed["password"], "sample:secret\\value")
        self.assertEqual(parsed["host"], "127.0.0.1")
        self.assertEqual(parsed["dbname"], "riverview")
        self.assertEqual(parsed["user"], "riverview_core")
        self.assertIn("default_transaction_read_only=on", parsed["options"])
        self.assertNotIn("passfile", parsed)
        self.assertEqual(os.environ.get("PGPASSFILE"), before)

    def test_existing_read_apis_receive_password_conninfo_not_passfile(self):
        dsn = module._readonly_dsn(b"127.0.0.1:5432:riverview:riverview_core:synthetic\n")
        with mock.patch.object(psycopg, "connect", side_effect=[_Connection(), _Connection()]) as connect:
            AuthorityRegistry(dsn, schema="riverview_authority", runtime_safe=True)
            PostgresLedger(dsn, schema="riverview_dev")
        self.assertEqual(connect.call_count, 2)
        for call in connect.call_args_list:
            parsed = conninfo_to_dict(call.args[0])
            self.assertEqual(parsed["password"], "synthetic")
            self.assertNotIn("passfile", parsed)
            self.assertIn("default_transaction_read_only=on", parsed["options"])

    def test_pgpass_target_mismatch_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "database_credential_target_mismatch"):
            module._pgpass_password(b"127.0.0.1:5432:other:riverview_core:value\n")

    def test_malformed_or_multiline_pgpass_fails_closed(self):
        for raw in (b"", b"127.0.0.1:5432:riverview:riverview_core:x",
                    b"127.0.0.1:5432:riverview:riverview_core:x\nextra\n"):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(RuntimeError, "database_credential_format_invalid"):
                    module._pgpass_password(raw)


if __name__ == "__main__":
    unittest.main()

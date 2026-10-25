# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_migrate_institutional_authority.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Verify the fixed authority release command uses the existing migration runner
# Execution Model: Unit test with a patched migration runner
# Authority: Never connects to a database or changes production
# =============================================================================
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import migrate_institutional_authority


class AuthorityMigrationCommandTests(unittest.TestCase):
    def test_fixed_release_command_uses_existing_authority_migration_runner(self):
        output = io.StringIO()
        with patch.object(migrate_institutional_authority.os, "geteuid", return_value=0), \
                patch.object(migrate_institutional_authority, "apply_migrations",
                             return_value=[]) as apply, \
                contextlib.redirect_stdout(output):
            self.assertEqual(migrate_institutional_authority.main(), 0)
        root = Path(migrate_institutional_authority.__file__).resolve().parents[1]
        apply.assert_called_once_with(
            "dbname=riverview", schema="riverview_authority",
            migrations_dir=root / "src/riverview_core/institutional_authority/migrations")
        self.assertIn('"declarations_reconciled": true', output.getvalue())
        self.assertIn('"versions": []', output.getvalue())


if __name__ == "__main__":
    unittest.main()

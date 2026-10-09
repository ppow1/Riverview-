# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_migrate_document_revisions.py
# Component: ENG-REVISION-CONTROL
# Revision: 1.0.3
# Purpose: Verify non-destructive documentation revision migration
# Execution Model: Request-driven tests
# Observability: unittest results and exit status
# Dependencies: Python 3.10+, standard library
# Authority: Temporary directories only
# Changed: 2026-10-09 UTC | ENG-REV-002 | Repair malformed test fixture line breaks
# Contracts: docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
# Tests: This file
# History: Git and predecessor archive
# =============================================================================
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('migration',Path(__file__).resolve().parents[1]/'scripts'/'migrate_document_revisions.py')
migration=importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.archive=self.root/'baseline.tar'
        with tarfile.open(self.archive,'w') as tar:
            for name,data in {'README.md':b'# README\nContent\n',
                              'docs/old.md':b'**Revision:** Rev 1.3\nOriginal\n',
                              'docs/heading.md':b'# Riverview~ Engineering Records Standard — Rev 1.0\nText\n'}.items():
                info=tarfile.TarInfo(name)
                info.size=len(data)
                tar.addfile(info,io.BytesIO(data))
    def test_preserves_and_migrates(self):
        report=migration.migrate(self.archive,self.root/'out')
        self.assertEqual((report['documents'],report['changed'],report['unchanged']),(3,1,2))
        self.assertEqual((self.root/'out/original/README.md').read_bytes(),b'# README\nContent\n')
        self.assertTrue((self.root/'out/staged/README.md').read_bytes().endswith(b'# README\nContent\n'))
        self.assertEqual((self.root/'out/staged/docs/old.md').read_bytes(),b'**Revision:** Rev 1.3\nOriginal\n')
    def test_heading_revision_preserved(self):
        migration.migrate(self.archive,self.root/'out')
        self.assertEqual(
            (self.root/'out/staged/docs/heading.md').read_bytes(),
            '# Riverview~ Engineering Records Standard — Rev 1.0\nText\n'.encode('utf-8')
        )
    def test_rejects_overwrite(self):
        migration.migrate(self.archive,self.root/'out')
        with self.assertRaises(ValueError):
            migration.migrate(self.archive,self.root/'out')

if __name__=='__main__':
    unittest.main()

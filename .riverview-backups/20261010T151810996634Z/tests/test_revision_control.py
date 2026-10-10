# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_revision_control.py
# Component: ENG-REVISION-CONTROL
# Revision: 1.2.1
# Purpose: Regression tests for revision validation and predecessor preservation
# Execution Model: Request-driven tests
# Observability: unittest results and exit code
# Dependencies: Python 3.10+, Git
# Authority: Temporary repositories only
# Changed: 2026-10-09 UTC | ENG-REV-001 | Cover bold Markdown and legacy revision headers
# Contracts: docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
# Tests: This file
# History: Git and revision backup manifest
# =============================================================================
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('rev',Path(__file__).resolve().parents[1]/'scripts'/'revision_control.py')
rev=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rev)

class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.file=self.root/'sample.py'
        self.file.write_text('# Revision: 1.0.0\nprint(1)\n')
        subprocess.run(['git','-C',str(self.root),'add','sample.py'],check=True)
        self.base=self.root/'baseline.json'
        self.base.write_text(json.dumps({'files':rev.inventory(self.root)}))
    def issues(self):
        return [x['issue'] for x in rev.check(self.root,self.base)]
    def test_legacy_markdown_revision(self):
        self.file.write_text('**Revision:** Rev 1.3\n')
        self.assertEqual(rev.revision(self.root,'sample.py'),'1.3')
    def test_legacy_markdown_document_revision(self):
        self.file.write_text('**Document Revision:** Rev 1.3\\n')
        self.assertEqual(rev.revision(self.root,'sample.py'),'1.3')
    def test_legacy_revision_comparison(self):
        self.assertTrue(rev.inc('1.3','1.4'))
        self.assertFalse(rev.inc('1.3','1.3'))
    def test_inventory(self):
        self.assertEqual(rev.inventory(self.root)[0]['revision'],'1.0.0')
    def test_changed_without_bump_fails(self):
        self.file.write_text('# Revision: 1.0.0\nprint(2)\n')
        self.assertIn('revision_not_incremented',self.issues())
    def test_bump_without_backup_fails(self):
        self.file.write_text('# Revision: 1.0.1\nprint(2)\n')
        self.assertIn('predecessor_backup_missing_or_invalid',self.issues())
    def test_bump_with_backup_passes(self):
        rev.backup(self.root,'sample.py','TASK-1')
        self.file.write_text('# Revision: 1.0.1\nprint(2)\n')
        self.assertEqual(self.issues(),[])
    def test_tampered_backup_fails(self):
        record=rev.backup(self.root,'sample.py','TASK-1')
        (self.root/record['backup']).write_text('tampered')
        self.file.write_text('# Revision: 1.0.1\nprint(2)\n')
        self.assertIn('predecessor_backup_missing_or_invalid',self.issues())
    def test_backup_exact_and_logged(self):
        old=self.file.read_bytes()
        result=rev.backup(self.root,'sample.py','TASK-1')
        self.assertEqual((self.root/result['backup']).read_bytes(),old)
        self.assertEqual(len((self.root/'.riverview-backups/manifest.jsonl').read_text().splitlines()),1)
    def test_backup_rejects_traversal(self):
        with self.assertRaises(ValueError): rev.backup(self.root,'../bad','TASK-1')

if __name__=='__main__': unittest.main()

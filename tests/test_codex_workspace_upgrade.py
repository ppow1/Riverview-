# Riverview Controlled Test
# File: tests/test_codex_workspace_upgrade.py
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.1
# Changed: 2026-10-28 | RV-CODEX-ENGINEERING-WRITE | Cover existing private-primary-group directories and unsafe ancestry.
# Purpose: Verify predecessor preservation, rollback, and isolated checkout creation.
# Execution Model: Offline temporary directories; no SSH, credentials or model calls.
# Authority: Disposable files only.
# Changed: 2026-10-28 | RV-CODEX-ENGINEERING-WRITE
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

path=Path(__file__).resolve().parents[1]/'scripts/upgrade_camrui_codex_workspace.py'
spec=importlib.util.spec_from_file_location('upgrade',path)
upgrade=importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.installed=self.root/'installed'
        self.source=self.root/'source'
        self.installed.mkdir()
        self.source.mkdir()
        self.expected={}
        for name in ('entry.py','helper.py'):
            old=b"# old\n"
            (self.installed/name).write_bytes(old)
            (self.source/name).write_bytes(b"# new\n")
            self.expected[name]=hashlib.sha256(old).hexdigest()

    def test_install_preserves_verified_originals_and_new_files(self):
        result=upgrade.replace_files(self.installed,self.source,self.root/'backup',self.expected)
        for name in self.expected:
            self.assertEqual((self.installed/name).read_bytes(),b"# new\n")
            self.assertEqual((self.root/'backup'/name).read_bytes(),b"# old\n")
            self.assertEqual(result['predecessors'][name],self.expected[name])

    def test_existing_775_private_primary_group_is_accepted_without_chmod(self):
        self.installed.chmod(0o775)
        workspace=self.root/'workspace'
        with patch.object(Path,'home',return_value=self.root), \
                patch.object(upgrade,'private_primary_group',return_value=True):
            upgrade.validate_paths(self.installed,workspace)
        self.assertEqual(self.installed.stat().st_mode & 0o777,0o775)

    def test_group_shared_world_writable_and_symlink_paths_are_rejected(self):
        for mode in (0o775,0o777):
            self.installed.chmod(mode)
            with self.subTest(mode=mode),patch.object(Path,'home',return_value=self.root), \
                    patch.object(upgrade,'private_primary_group',return_value=False), \
                    self.assertRaises(ValueError):
                upgrade.validate_paths(self.installed,self.root/'workspace')
        self.installed.chmod(0o700)
        link=self.root/'link'
        link.symlink_to(self.installed,target_is_directory=True)
        with patch.object(Path,'home',return_value=self.root),self.assertRaises(ValueError):
            upgrade.validate_paths(link,self.root/'workspace')

    def test_primary_group_rejects_supplementary_or_primary_other_members(self):
        user=SimpleNamespace(pw_uid=1001,pw_gid=1001,pw_name='admin1')
        other=SimpleNamespace(pw_uid=1002,pw_gid=1001,pw_name='other')
        with patch.object(upgrade.pwd,'getpwuid',return_value=user), \
                patch.object(upgrade.pwd,'getpwall',return_value=[user]) as accounts, \
                patch.object(upgrade.grp,'getgrgid',return_value=SimpleNamespace(gr_mem=['admin1'])) as group:
            self.assertTrue(upgrade.private_primary_group(1001,1001))
            group.return_value=SimpleNamespace(gr_mem=['admin1','other'])
            self.assertFalse(upgrade.private_primary_group(1001,1001))
            group.return_value=SimpleNamespace(gr_mem=[])
            accounts.return_value=[user,other]
            self.assertFalse(upgrade.private_primary_group(1001,1001))

    def test_unexpected_predecessor_refuses_without_replacement(self):
        (self.installed/'entry.py').write_text('# changed')
        with self.assertRaises(ValueError):
            upgrade.replace_files(self.installed,self.source,self.root/'backup',self.expected)
        self.assertEqual((self.installed/'helper.py').read_bytes(),b"# old\n")
        self.assertFalse((self.root/'backup').exists())

    def test_partial_replacement_rolls_back(self):
        real=upgrade.os.replace
        calls=[]
        def replace(source,target):
            calls.append(target)
            if len(calls)==2:
                raise OSError('simulated replacement failure')
            return real(source,target)
        with patch.object(upgrade.os,'replace',side_effect=replace):
            with self.assertRaises(OSError):
                upgrade.replace_files(self.installed,self.source,self.root/'backup',self.expected)
        for name in self.expected:
            self.assertEqual((self.installed/name).read_bytes(),b"# old\n")

    def test_separate_clone_uses_exact_revision_and_does_not_reset_existing_edits(self):
        repo=self.root/'repo'
        subprocess.run(['git','init','-q',str(repo)],check=True)
        (repo/'sample.txt').write_text('baseline')
        upgrade.git('-C',repo,'add','sample.txt')
        upgrade.git('-C',repo,'-c','user.name=Test','-c','user.email=test@example.invalid',
                    'commit','-qm','test baseline')
        revision=upgrade.git('-C',repo,'rev-parse','HEAD')
        workspace=self.root/'workspace'
        self.assertEqual(upgrade.prepare_workspace(repo,workspace,revision),revision)
        self.assertTrue((workspace/'.git').is_dir())
        (workspace/'sample.txt').write_text('engineering edit')
        self.assertEqual(upgrade.prepare_workspace(repo,workspace,revision),revision)
        self.assertEqual((workspace/'sample.txt').read_text(),'engineering edit')
        self.assertEqual((repo/'sample.txt').read_text(),'baseline')


if __name__=='__main__':
    unittest.main()

# Riverview Controlled Source
# File: tests/test_ssh_codex_entry.py
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: Verify restricted request parsing and fingerprint-bound authorized-key edits.
# Execution Model: Offline unittest with temporary files; no SSH, credentials or model calls.
# Observability: Test results and exit code.
# Dependencies: Python standard library and proposed commissioning scripts.
# Authority: No production state is touched.
# Changed: 2026-10-27 | RV-CAMRUI-GATEWAY-CODEX | Initial boundary regression checks.
# History: New file; no predecessor.
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch


def load(name):
    path=Path(__file__).resolve().parents[1]/'scripts'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entry=load('ssh_codex_entry')
installer=load('commission_camrui_codex_entry')


class EntryTests(unittest.TestCase):
    def request(self, **fields):
        return entry.parse_request('rv-codex-session '+shlex.quote(json.dumps(fields)))

    def test_preserves_hostname_probe(self):
        self.assertEqual(entry.parse_request('hostname'), {'operation':'hostname'})

    def test_start_and_resume_have_fixed_identity_model_and_cwd(self):
        request=self.request(operation='start',run_id='acceptance-1',prompt='hello; $(id)')
        argv=entry.cli_arguments(request)
        self.assertEqual(argv[argv.index('--codex')+1],'/home/admin1/.local/bin/codex')
        self.assertEqual(argv[argv.index('--cwd')+1],'/home/admin1')
        self.assertEqual(argv[argv.index('--model')+1],'gpt-6-luna')
        self.assertEqual(argv[argv.index('--prompt')+1],'hello; $(id)')
        thread='01a17fd0-a4ae-73a2-9f0c-9f864cd82102'
        resume=self.request(operation='resume',run_id='acceptance-2',prompt='continue',thread_id=thread)
        self.assertEqual(entry.cli_arguments(resume)[-2:],['--resume',thread])

    def test_rejects_shell_and_unknown_fields(self):
        for command in ('sh -c id','hostname; id','rv-codex-session {} ; id',''):
            with self.subTest(command=command),self.assertRaises(ValueError):
                entry.parse_request(command)
        with self.assertRaises(ValueError):
            self.request(operation='start',run_id='a',prompt='hello',codex='/bin/sh')

    def test_rejects_traversal_duplicate_fields_and_invalid_thread(self):
        for run in ('.','..','../other','a/b'):
            with self.subTest(run=run),self.assertRaises(ValueError):
                self.request(operation='status',run_id=run)
        with self.assertRaises(ValueError):
            entry.parse_request('rv-codex-session '+shlex.quote('{"operation":"identity","operation":"status"}'))
        with self.assertRaises(ValueError):
            self.request(operation='resume',run_id='a',prompt='continue',thread_id='--last')

    def test_result_returns_only_fixed_run_messages(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(entry,'STATE',Path(directory)):
            run=Path(directory)/'run1'
            run.mkdir()
            (run/'result.json').write_text(json.dumps({'status':'completed','exit_code':0,'events':'/etc/passwd'}))
            event={'type':'item.completed','item':{'type':'agent_message','text':'MARKER'}}
            (run/'events.jsonl').write_text(json.dumps(event)+'\n')
            result=entry.read_result({'run_id':'run1'})
            self.assertEqual(result['messages'],['MARKER'])


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.key=base64.b64encode(b'test-public-key-blob').decode()
        fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(b'test-public-key-blob').digest()).decode().rstrip('=')
        self.patcher=patch.object(installer,'EXPECTED',fingerprint)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.operator='ssh-ed25519 '+base64.b64encode(b'other-operator-key').decode()+' operator\n'

    def test_only_matching_forced_command_changes(self):
        old=self.operator+'restrict,command="hostname",from="192.168.1.88" ssh-ed25519 '+self.key+' gateway\n'
        new,summary=installer.replacement(old.encode())
        self.assertTrue(new.decode().startswith(self.operator))
        self.assertIn('restrict,command="'+installer.FORCED+'",from="192.168.1.88"',new.decode())
        self.assertIn(self.key+' gateway\n',new.decode())
        self.assertEqual(summary['line'],2)

    def test_missing_ambiguous_unrestricted_and_unexpected_entries_refuse(self):
        known='restrict,command="hostname" ssh-ed25519 '+self.key+' gateway\n'
        variants=[self.operator,known+known,'command="hostname" ssh-ed25519 '+self.key+'\n',
                  'restrict,command="/bin/sh" ssh-ed25519 '+self.key+'\n']
        for data in variants:
            with self.subTest(data=data),self.assertRaises(ValueError):
                installer.replacement(data.encode())


if __name__=='__main__':
    unittest.main()

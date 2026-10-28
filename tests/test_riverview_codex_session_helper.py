# Riverview Controlled Source
# File: tests/test_riverview_codex_session_helper.py
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.1
# Purpose: Offline verification of CLI invocation, output capture and exact resume binding.
# Execution Model: unittest with disposable fake child process, no network or credentials.
# Observability: unittest results and exit codes.
# Dependencies: Python standard library; scripts/riverview_codex_session.py.
# Authority: Temporary test directories only; never invokes real Codex.
# Changed: 2026-10-27 | RV-CODEX-DUAL-HOST-RUNBOOK | Initial helper verification.
# History: New file; no predecessor.
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1]/'scripts/riverview_codex_session.py'
THREAD = '01a17ee1-4a3b-7951-b26d-3f44ecda6c25'


class SessionHelperTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fake = self.root/'fake_cli.py'
        self.fake.write_text('''import json,sys
from pathlib import Path
prompt=sys.stdin.read()
argv=sys.argv[1:]
assert argv[:5]==['--ask-for-approval','never','exec','--sandbox','workspace-write']
assert argv[argv.index('--cd')+1]==str(Path.cwd())
assert 'exec' in argv
assert argv[-1]=='-'
assert argv[argv.index('--model')+1]=='gpt-6-luna'
counter=Path('calls.txt')
counter.write_text(str(int(counter.read_text())+1) if counter.exists() else '1')
thread='01a17ee1-4a3b-7951-b26d-3f44ecda6c25'
if 'resume' in argv: assert thread in argv
print(json.dumps({'type':'thread.started','thread_id':thread}),flush=True)
print(json.dumps({'type':'item.completed','item':{'text':'FAKE_RESULT'}}),flush=True)
print('normal fake diagnostic',file=sys.stderr)
if 'fail' in prompt: sys.exit(7)
''')

    def invoke(self, run='first', prompt='first step', resume=None):
        command=[sys.executable,str(HELPER),'--codex',str(self.fake),'--node',sys.executable,
            '--cwd',str(self.root),'--state-root',str(self.root/'state'),'--run-id',run,
            '--host-label','camrui','--non-repository-smoke-test','--prompt',prompt]
        if resume:
            command+=['--resume',resume]
        return subprocess.run(command,capture_output=True,text=True)

    def test_start_retains_events_stderr_and_thread(self):
        result=self.invoke()
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['thread_id'],THREAD)
        self.assertEqual(value['status'],'completed')
        self.assertIn('FAKE_RESULT',Path(value['events']).read_text())
        self.assertIn('normal fake diagnostic',(self.root/'state/first/stderr.txt').read_text())

    def test_resume_uses_exact_prior_thread(self):
        prior=self.invoke()
        self.assertEqual(prior.returncode,0)
        result=self.invoke('second','follow-up',json.loads(prior.stdout)['thread_id'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['thread_id'],THREAD)
        self.assertEqual((self.root/'calls.txt').read_text(),'2')

    def test_idempotent_run_does_not_execute_twice(self):
        self.assertEqual(self.invoke().returncode,0)
        self.assertEqual(self.invoke().returncode,0)
        self.assertEqual((self.root/'calls.txt').read_text(),'1')

    def test_changed_request_same_id_fails_before_execution(self):
        self.assertEqual(self.invoke().returncode,0)
        result=self.invoke(prompt='different request')
        self.assertEqual(result.returncode,2)
        self.assertIn('run_id_conflict',result.stderr)
        self.assertEqual((self.root/'calls.txt').read_text(),'1')

    def test_child_failure_propagates_exit_status(self):
        result=self.invoke(prompt='fail')
        self.assertEqual(result.returncode,7)
        self.assertEqual(json.loads(result.stdout)['status'],'failed')


if __name__=='__main__':
    unittest.main()

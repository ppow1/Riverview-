#!/usr/bin/env python3
# Riverview Controlled Source
# File: scripts/riverview_codex_session.py
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: Invoke the existing Codex CLI and retain JSON events and exact resume ID.
# Execution Model: Request-driven CLI; existing Comms5 owns asynchronous execution.
# Observability: Per-run request.json, events.jsonl, stderr.txt, result.json; JSON stdout.
# Dependencies: Python 3.10+, authenticated existing Codex CLI; optional Node executable.
# Authority: Current OS account; read-only Codex sandbox; no credentials or grants changed.
# Changed: 2026-10-27 | RV-CODEX-DUAL-HOST-RUNBOOK | Portable invocation/logging helper.
# Contracts: docs/operations/CODEX_DUAL_HOST_CONTROL_RUNBOOK.md
# Tests: Offline fake-CLI start/resume and idempotency checks; live host tests outstanding.
# History: New file; no predecessor.
"""Thin invocation helper, not a dispatcher, credential manager, or PTY service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', required=True, help='Existing Codex executable or codex.js')
    parser.add_argument('--node', help='Existing Node executable; required for codex.js')
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--state-root', required=True, help='Account-owned output directory')
    parser.add_argument('--run-id', required=True, help='Stable identifier for this invocation')
    parser.add_argument('--host-label', required=True, choices=['desktop-ja3rpnq', 'camrui'])
    parser.add_argument('--model', default='gpt-6-luna')
    parser.add_argument('--prompt', required=True, help='Do not include secrets')
    parser.add_argument('--resume', help='Exact completed Codex thread UUID; never use --last')
    parser.add_argument('--non-repository-smoke-test', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', args.run_id):
        parser.error('run-id must contain only letters, numbers, dots, underscores or hyphens')
    if args.resume and not re.fullmatch(r'[0-9a-fA-F-]{36}', args.resume):
        parser.error('resume must be the exact recorded UUID')
    cwd = Path(args.cwd).resolve(strict=True)
    if not cwd.is_dir():
        parser.error('cwd must be a directory')
    command = [args.codex]
    if args.node:
        command = [args.node, args.codex]
    # Global sandbox applies to both exec and exec resume. Preserve existing auth.
    command += ['--sandbox', 'read-only', 'exec']
    if args.resume:
        command += ['resume']
    command += ['--json', '--model', args.model]
    if args.non_repository_smoke_test:
        command += ['--skip-git-repo-check']
    if args.resume:
        command += [args.resume]
    # Pass the prompt on stdin, avoiding platform-specific shell quoting.
    command += ['-']
    request = dict(host_label=args.host_label, cwd=str(cwd), command=command,
                   prompt_sha256=hashlib.sha256(args.prompt.encode()).hexdigest())
    root = Path(args.state_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    run = root / args.run_id
    try:
        run.mkdir()
    except FileExistsError:
        prior = run / 'request.json'
        if not prior.is_file() or json.loads(prior.read_text()) != request:
            print('run_id_conflict', file=sys.stderr)
            return 2
        result = run / 'result.json'
        if result.is_file():
            value = json.loads(result.read_text())
            print(json.dumps(value))
            return value.get('exit_code', 2) if value.get('status') != 'running' else 2
        print('existing_run_requires_inspection', file=sys.stderr)
        return 2
    write_json(run / 'request.json', request)
    result = dict(status='starting', host_label=args.host_label, cwd=str(cwd),
                  run_id=args.run_id, thread_id=args.resume, events=str(run/'events.jsonl'))
    write_json(run / 'result.json', result)
    try:
        with (run/'events.jsonl').open('w', encoding='utf-8') as events, \
                (run/'stderr.txt').open('w', encoding='utf-8') as errors:
            process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=errors, text=True, encoding='utf-8')
            result.update(status='running', pid=process.pid)
            write_json(run/'result.json', result)
            process.stdin.write(args.prompt + '\n')
            process.stdin.close()
            for line in process.stdout:
                events.write(line)
                events.flush()
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get('type') == 'thread.started' and event.get('thread_id'):
                    thread = event['thread_id']
                    if args.resume and thread != args.resume:
                        result['thread_mismatch'] = True
                    result['thread_id'] = thread
                    write_json(run/'result.json', result)
            code = process.wait()
            result.update(status='completed' if code == 0 else 'failed', exit_code=code)
            if not result.get('thread_id') or result.get('thread_mismatch'):
                result.update(status='failed', exit_code=2, diagnostic='thread_identity_not_verified')
    except (OSError, UnicodeError) as exc:
        result.update(status='failed', exit_code=2, diagnostic=type(exc).__name__)
    write_json(run/'result.json', result)
    print(json.dumps(result))
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())

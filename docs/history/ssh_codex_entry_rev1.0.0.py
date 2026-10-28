#!/usr/bin/env python3
# Riverview Controlled Source
# File: scripts/ssh_codex_entry.py
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: Proposed restricted SSH entry for existing Gateway Codex control.
# Execution Model: Forced command; existing SSH and Comms5 own transport/lifecycle.
# Observability: Bounded JSON replies and existing account-local CLI artifacts.
# Dependencies: Existing riverview_codex_session.py, admin1 Codex installation/login.
# Authority: No arbitrary shell; existing hostname probe plus typed read-only Codex calls.
# Changed: 2026-10-27 | RV-CAMRUI-GATEWAY-CODEX | Prepared, not installed.
# Tests: tests/test_ssh_codex_entry.py; live commissioning requires Steward approval.
# History: New file; no predecessor.
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys

INSTALL = Path('/home/admin1/.local/lib/riverview/gateway-codex')
STATE = Path('/home/admin1/.local/state/riverview/gateway-codex')
CODEX = '/home/admin1/.local/bin/codex'
RUN = re.compile(r'[A-Za-z0-9._-]{1,100}')
THREAD = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}')


def parse_request(original):
    if not isinstance(original, str) or len(original.encode()) > 7000:
        raise ValueError('request_size')
    if original.strip() == 'hostname':
        return {'operation': 'hostname'}
    words = shlex.split(original)
    if len(words) != 2 or words[0] != 'rv-codex-session':
        raise ValueError('unsupported_command')
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_field')
            result[key] = value
        return result
    request = json.loads(words[1], object_pairs_hook=unique_keys)
    if not isinstance(request, dict):
        raise ValueError('request_object')
    operation = request.get('operation')
    fields = {'identity': {'operation'}, 'status': {'operation', 'run_id'},
              'start': {'operation', 'run_id', 'prompt'},
              'resume': {'operation', 'run_id', 'prompt', 'thread_id'}}
    if operation not in fields or set(request) != fields[operation]:
        raise ValueError('request_fields')
    if 'run_id' in request and (not isinstance(request['run_id'], str) or
                               not RUN.fullmatch(request['run_id']) or
                               request['run_id'] in {'.', '..'}):
        raise ValueError('run_id')
    if 'prompt' in request and (not isinstance(request['prompt'], str) or
                               not request['prompt'].strip() or
                               len(request['prompt'].encode()) > 4000 or
                               '\x00' in request['prompt']):
        raise ValueError('prompt')
    if 'thread_id' in request and (not isinstance(request['thread_id'], str) or
                                  not THREAD.fullmatch(request['thread_id'])):
        raise ValueError('thread_id')
    return request


def cli_arguments(request):
    command = [sys.executable, str(INSTALL/'riverview_codex_session.py'),
        '--codex', CODEX, '--cwd', '/home/admin1', '--state-root', str(STATE),
        '--run-id', request['run_id'], '--host-label', 'camrui',
        '--model', 'gpt-6-luna', '--non-repository-smoke-test', '--prompt', request['prompt']]
    if request['operation'] == 'resume':
        command += ['--resume', request['thread_id']]
    return command


def read_result(request):
    run = STATE/request['run_id']
    if STATE.is_symlink() or run.is_symlink():
        raise ValueError('symlink_state')
    result_path = run/'result.json'
    if result_path.is_symlink():
        raise ValueError('symlink_result')
    if not result_path.is_file():
        return {'status': 'not_found', 'run_id': request['run_id']}
    if result_path.stat().st_size > 16384:
        raise ValueError('result_size')
    result = json.loads(result_path.read_text())
    if not isinstance(result, dict):
        raise ValueError('result_shape')
    # Read only this validated run's fixed event path, never a path supplied in JSON.
    messages = []
    events = run/'events.jsonl'
    if events.is_symlink():
        raise ValueError('symlink_events')
    if events.is_file():
        if events.stat().st_size > 4 * 1024 * 1024:
            result['events_status'] = 'too_large_for_bounded_result'
        if events.stat().st_size <= 4 * 1024 * 1024:
            with events.open() as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    item = event.get('item')
                    if (event.get('type') == 'item.completed' and isinstance(item, dict)
                            and item.get('type') == 'agent_message'
                            and isinstance(item.get('text'), str)):
                        messages.append(item['text'][:1000])
                        messages = messages[-8:]
    return {**result, 'messages': messages}


def main():
    try:
        request = parse_request(os.environ.get('SSH_ORIGINAL_COMMAND', ''))
        operation = request['operation']
        if operation == 'hostname':
            print(socket.gethostname())
            return 0
        if operation == 'identity':
            import pwd
            print(json.dumps({'status': 'available', 'marker': 'RV_GATEWAY_CODEX_ENTRY_OK',
                'hostname': socket.gethostname(), 'user': pwd.getpwuid(os.getuid()).pw_name,
                'cwd': '/home/admin1', 'protocol': 'rv-codex-session.v1'}))
            return 0
        if operation == 'status':
            print(json.dumps(read_result(request)))
            return 0
        # argv only: SSH_ORIGINAL_COMMAND is never evaluated by a shell.
        return subprocess.run(cli_arguments(request), shell=False).returncode
    except (ValueError, OSError, TypeError, KeyError):
        print(json.dumps({'status': 'denied', 'reason': 'bounded_request_or_state_invalid'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

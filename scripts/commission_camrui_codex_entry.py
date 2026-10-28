#!/usr/bin/env python3
# Riverview Controlled Source
# File: scripts/commission_camrui_codex_entry.py
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: Prepare one fingerprint-bound forced-command change; default is dry run.
# Execution Model: Explicit operator commissioning under admin1, no daemon or sudo.
# Observability: Proposed key option diff, verified backup hashes, restoration metadata.
# Dependencies: Python standard library; adjacent entry and existing CLI helper source.
# Authority: --apply AND --acknowledge-key-scope-change require separate Steward approval.
# Changed: 2026-10-27 | RV-CAMRUI-GATEWAY-CODEX | Prepared, not installed.
# Tests: tests/test_ssh_codex_entry.py; no live authorized_keys mutation performed.
# History: New file; no predecessor.
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import tempfile

EXPECTED = 'SHA256:mqhE3Ax4u/FDvAQlVZzw9Hs5TMO+aDtUYPdiEJqMUPo'
ROOT = Path('/home/admin1/.local/lib/riverview/gateway-codex')
FORCED = '/usr/bin/python3 /home/admin1/.local/lib/riverview/gateway-codex/ssh_codex_entry.py'


def replacement(data):
    lines = data.decode('utf-8').splitlines(keepends=True)
    matches = []
    for number, line in enumerate(lines):
        match = re.fullmatch(r'(.*?)\s+(ssh-ed25519)\s+([A-Za-z0-9+/=]+)([^\r\n]*)(\r?\n)?', line)
        if not match:
            continue
        try:
            key = base64.b64decode(match[3], validate=True)
        except ValueError:
            continue
        fingerprint = 'SHA256:' + base64.b64encode(hashlib.sha256(key).digest()).decode().rstrip('=')
        if fingerprint != EXPECTED:
            continue
        options = match[1]
        if not re.search(r'(^|,)restrict(?=,|$)', options):
            raise ValueError('expected key lacks restrict; refuse')
        pattern = r'(^|,)command="(?:/usr/bin/|/bin/)?hostname"(?=,|$)'
        if len(re.findall(pattern, options)) != 1:
            raise ValueError('expected key is not exactly the known hostname-only entry; refuse')
        candidate_options = re.sub(pattern, lambda m: m[1]+'command="'+FORCED+'"', options)
        candidate = candidate_options + line[len(options):]
        matches.append((number, options, candidate_options, candidate))
    if len(matches) != 1:
        raise ValueError('expected exactly one matching restricted Gateway key; refuse')
    number, before, after, candidate = matches[0]
    lines[number] = candidate
    return ''.join(lines).encode(), {'line': number+1, 'fingerprint': EXPECTED,
                                     'before_options': before, 'after_options': after}


def owned_private(path, directory=False):
    if path.is_symlink():
        raise ValueError('symlink refused: '+str(path))
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('expected current-user private path: '+str(path))
    if directory and not path.is_dir():
        raise ValueError('expected directory')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--acknowledge-key-scope-change', action='store_true')
    args = parser.parse_args()
    if pwd.getpwuid(os.getuid()).pw_name != 'admin1' or Path.home() != Path('/home/admin1'):
        parser.error('run only as the established admin1 operator identity')
    auth = Path.home()/'.ssh/authorized_keys'
    owned_private(auth.parent, directory=True)
    owned_private(auth)
    original = auth.read_bytes()
    candidate, summary = replacement(original)
    source = Path(__file__).resolve().parent
    sources = {name: (source/name).read_bytes() for name in
               ('ssh_codex_entry.py', 'riverview_codex_session.py')}
    for name, content in sources.items():
        compile(content, name, 'exec')
    summary.update(status='prepared', mode='dry_run',
        predecessor_sha256=hashlib.sha256(original).hexdigest(),
        candidate_sha256=hashlib.sha256(candidate).hexdigest(),
        files={name:hashlib.sha256(content).hexdigest() for name,content in sources.items()},
        warning='Changes this existing key from hostname-only to bounded read-only Codex control.')
    if not args.apply:
        print(json.dumps(summary, indent=2))
        return 0
    if not args.acknowledge_key_scope_change:
        parser.error('explicit scope-change acknowledgement required; no files changed')
    # Refuse to replace an existing installation or loosen existing path permissions.
    if ROOT.exists() or ROOT.is_symlink():
        parser.error('installation already exists; preserve and review it separately')
    for parent in ROOT.parents:
        if parent == Path.home():
            break
        if parent.exists() and (parent.is_symlink() or parent.stat().st_uid != os.getuid()
                               or parent.stat().st_mode & 0o022):
            parser.error('unsafe installation ancestor: '+str(parent))
    backup = Path.home()/'.local/state/riverview/gateway-codex-commissioning'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True, mode=0o700)
    saved = backup/'authorized_keys'
    saved.write_bytes(original)
    saved.chmod(0o600)
    if saved.read_bytes() != original:
        raise RuntimeError('backup read-back failed')
    manifest = {**summary, 'restore': 'Verify predecessor_sha256, then atomically restore backup authorized_keys to /home/admin1/.ssh/authorized_keys preserving owner/mode.',
                'target': str(auth), 'backup': str(saved), 'revision': '1.0.0'}
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (backup/'manifest.json').chmod(0o600)
    ROOT.mkdir(parents=True, mode=0o700)
    for name, content in sources.items():
        target = ROOT/name
        target.write_bytes(content)
        target.chmod(0o700)
        if target.read_bytes() != content:
            raise RuntimeError('installed source read-back failed')
    if auth.read_bytes() != original:
        raise RuntimeError('authorized_keys changed concurrently; no key replacement performed')
    descriptor, temporary = tempfile.mkstemp(dir=auth.parent, prefix='.rv-codex-key-')
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(candidate)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(auth.stat().st_mode))
        os.replace(temporary, auth)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    if auth.read_bytes() != candidate:
        raise RuntimeError('key replacement read-back failed; restore verified backup')
    print(json.dumps({**summary, 'status':'installed', 'mode':'apply', 'backup':str(backup)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

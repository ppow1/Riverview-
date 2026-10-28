#!/usr/bin/env python3
# Riverview Controlled Source
# File: scripts/upgrade_camrui_codex_workspace.py
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: Replace the two installed read-only wrappers and create an isolated source checkout.
# Execution Model: Explicit operator update under existing admin1 SSH login; no service restart.
# Observability: Verified predecessor backup, file hashes, checkout revision and JSON result.
# Dependencies: Python standard library, existing Git source and installed Codex.
# Authority: Steward instruction to fix the launcher; no key, grant or production release changes.
# Changed: 2026-10-28 | RV-CODEX-ENGINEERING-WRITE
# History: New file; installer backups preserve actual installed predecessors.
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import tempfile

ROOT = Path('/home/admin1/.local/lib/riverview/gateway-codex')
WORKSPACE = Path('/home/admin1/.local/share/riverview/engineering/Riverview')
SOURCE = Path('/tmp/riverview-grace-worker-diagnostics')
REVISION = '9f56cb72f3bd2961babf2527a26bd843526e18ce'
EXPECTED = {
    'ssh_codex_entry.py': 'ac91f7474a0916e0d3d8529f91353b8eb72421eb7e69202abb954b7efd55db90',
    'riverview_codex_session.py': '9eee1d0dce6916ff8f85b8b693f7de078013112ea6a68b5a81f36a64effc6231',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *map(str, args)], text=True).strip()


def validate_paths(root, workspace):
    for target in (root, workspace):
        for path in (target, *target.parents):
            if path == Path('/home'):
                break
            if path.is_symlink():
                raise ValueError('symlink path refused: ' + str(path))
            if path.exists() and (path.stat().st_uid != os.getuid() or
                                  path.stat().st_mode & 0o022):
                raise ValueError('path must be owned and not group/world writable: ' + str(path))


def replace_files(root, source, backup, expected):
    originals = {}
    candidates = {}
    for name in expected:
        target = root/name
        if target.is_symlink():
            raise ValueError('symlink target refused')
        originals[name] = target.read_bytes()
        candidates[name] = (source/name).read_bytes()
        compile(candidates[name], name, 'exec')
        if digest(originals[name]) not in {expected[name], digest(candidates[name])}:
            raise ValueError('installed predecessor changed: ' + name)
    backup.mkdir(parents=True, mode=0o700)
    for name, data in originals.items():
        (backup/name).write_bytes(data)
        (backup/name).chmod(0o600)
        if (backup/name).read_bytes() != data:
            raise RuntimeError('backup verification failed')
    manifest = {
        'predecessors': {n:digest(v) for n,v in originals.items()},
        'installed': {n:digest(v) for n,v in candidates.items()},
        'restore': 'Verify predecessor hashes; atomically replace the two ROOT files from this backup. Keep the Engineering checkout and session state.',
        'root': str(root),
    }
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    changed = []
    try:
        for name, data in candidates.items():
            target = root/name
            if target.read_bytes() != originals[name]:
                raise RuntimeError('installed file changed concurrently')
            fd, temporary = tempfile.mkstemp(dir=root, prefix='.workspace-upgrade-')
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary,0o700)
                os.replace(temporary,target)
                changed.append(name)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            if target.read_bytes() != data:
                raise RuntimeError('installed verification failed')
    except Exception:
        for name in changed:
            (root/name).write_bytes(originals[name])
            (root/name).chmod(0o700)
        raise
    return manifest


def prepare_workspace(source, workspace, revision):
    if workspace.exists():
        if not (workspace/'.git').is_dir():
            raise ValueError('existing workspace is not the dedicated clone')
        git('-C',workspace,'cat-file','-e',revision+'^{commit}')
        return git('-C',workspace,'rev-parse','HEAD')
    git('-C',source,'cat-file','-e',revision+'^{commit}')
    workspace.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    # A separate clone keeps this workspace's Git metadata independent of the
    # original checkout and of every deployed production release.
    subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(source),str(workspace)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    git('-C',workspace,'checkout','--detach',revision)
    return git('-C',workspace,'rev-parse','HEAD')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if pwd.getpwuid(os.getuid()).pw_name != 'admin1' or Path.home()!=Path('/home/admin1'):
        parser.error('use the established admin1 operator SSH login')
    os.umask(0o077)
    validate_paths(ROOT,WORKSPACE)
    source=Path(__file__).resolve().parent
    for name, expected in EXPECTED.items():
        data=(ROOT/name).read_bytes()
        candidate=(source/name).read_bytes()
        compile(candidate,name,'exec')
        if digest(data) not in {expected,digest(candidate)}:
            parser.error('unexpected installed predecessor: '+name)
    git('-C',SOURCE,'cat-file','-e',REVISION+'^{commit}')
    if not args.apply:
        print(json.dumps({'status':'prepared','sandbox':'workspace-write','workspace':str(WORKSPACE),
                          'source_revision':REVISION,'authorized_keys':'unchanged'}))
        return 0
    revision=prepare_workspace(SOURCE,WORKSPACE,REVISION)
    backup=Path('/home/admin1/.local/state/riverview/gateway-codex-upgrades')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    manifest=replace_files(ROOT,source,backup,EXPECTED)
    print(json.dumps({'status':'installed','sandbox':'workspace-write','workspace':str(WORKSPACE),
                      'checkout_revision':revision,'backup':str(backup),
                      'authorized_keys':'unchanged',**manifest},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())

# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/revision_control.py
# Component: ENG-REVISION-CONTROL
# Revision: 1.2.4
# Purpose: Inventory file revisions and verify preserved predecessor backups
# Execution Model: Request-driven CLI; suitable for unattended CI and Camrui
# Observability: JSON stdout and exit codes
# Dependencies: Python 3.10+, Git
# Authority: Local checkout only; never edits source or remote
# Changed: 2026-10-18 UTC | RV-C2-DOD-REMEDIATION-001 | Record source commit, target revision, and restore guidance in new backups
# Contracts: docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
# Tests: tests/test_revision_control.py
# History: Git and revision backup manifest
# =============================================================================
"""Riverview file revision inventory and predecessor backup validation."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REV = re.compile(r'(?im)^\s*(?:#|//|\*|<!--|--)?\s*(?:\*\*)?\s*(?:Document Revision|File Revision|Revision)\s*(?:\*\*)?\s*:\s*(?:\*\*)?\s*(?:Rev\s+)?(\d+\.\d+(?:\.\d+)?)\b')
EXCLUDED = {'.git', '.riverview-backups', '__pycache__', '.pytest_cache', '.venv'}
SIDE_EXT = {'.json', '.jsonl', '.toml', '.lock', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.bin', '.ico'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def valid_revision(value):
    return isinstance(value, str) and re.fullmatch(r"\d+\.\d+(?:\.\d+)?", value) is not None

def evidence_sidecar_revision(root, rel, data):
    """Return a revision only when its evidence sidecar verifies this file."""
    path = root / rel
    if path.name == 'artifacts.json':
        try:
            manifest = json.loads(data)
            candidate = manifest.get('manifest_revision')
            return candidate if valid_revision(candidate) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
    if 'evidence' not in Path(rel).parts or 'checkouts' not in Path(rel).parts:
        return None
    sidecar = path.parent / 'artifacts.json'
    if not sidecar.is_file() or sidecar.is_symlink():
        return None
    try:
        manifest = json.loads(sidecar.read_text(encoding='utf-8'))
        entries = manifest.get('artifacts', manifest.get('files', {}))
        entry = entries.get(path.name)
        if not isinstance(entry, dict):
            return None
        if entry.get('sha256') != sha(data) or entry.get('size_bytes') != len(data):
            return None
        recorded_path = entry.get('path')
        if recorded_path and Path(recorded_path).name != path.name:
            return None
        candidate = entry.get('revision')
        return candidate if valid_revision(candidate) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None

def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=True).stdout

def tracked(root):
    return [p.decode() for p in git(root, 'ls-files', '-z').split(b'\0') if p]

def revision(root, rel, content=None):
    data = (root / rel).read_bytes() if content is None else content
    if Path(rel).suffix.lower() in SIDE_EXT:
        manifest = root / '.riverview-revisions.json'
        if manifest.exists():
            versioned = json.loads(manifest.read_text()).get('files', {}).get(rel, {}).get('revision')
            if versioned:
                return versioned
    if 'evidence' in Path(rel).parts and 'checkouts' in Path(rel).parts:
        try:
            header = REV.search(data.decode('utf-8')[:12000])
        except UnicodeDecodeError:
            header = None
        if header:
            return header.group(1)
        return evidence_sidecar_revision(root, rel, data)
    if Path(rel).suffix.lower() in SIDE_EXT:
        return None
    m = REV.search(data.decode('utf-8', errors='replace')[:12000])
    return m.group(1) if m and valid_revision(m.group(1)) else None

def inc(old, new):
    return old is not None and new is not None and tuple(map(int,(new+'.0').split('.')[:3])) > tuple(map(int,(old+'.0').split('.')[:3]))

def inventory(root):
    rows=[]
    for rel in tracked(root):
        if any(x in EXCLUDED for x in Path(rel).parts):
            continue
        p=root/rel
        if p.is_file():
            rows.append({'path':rel,'revision':revision(root,rel),'sha256':sha(p.read_bytes())})
    return rows

def backup(root, rel, task):
    if rel.startswith('/') or '..' in Path(rel).parts or rel.startswith('.riverview-backups/'):
        raise ValueError('Invalid path')
    path=root/rel
    if not path.is_file() or path.is_symlink():
        raise ValueError('Only existing regular files can be backed up')
    old=path.read_bytes()
    digest=sha(old)
    old_revision=revision(root,rel)
    if not old_revision or not valid_revision(old_revision):
        raise ValueError('A valid predecessor revision is required for a controlled backup')
    parts=old_revision.split('.')
    while len(parts)<3: parts.append('0')
    parts[-1]=str(int(parts[-1])+1)
    new_revision='.'.join(parts)
    source_commit=git(root,'rev-parse','HEAD').decode().strip()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    location=root/'.riverview-backups'/stamp/rel
    location.parent.mkdir(parents=True, exist_ok=True)
    with location.open('xb') as stream:
        stream.write(old)
    if location.read_bytes()!=old:
        raise RuntimeError('Backup verification failed')
    record={'path':rel,'revision':old_revision,'new_revision':new_revision,
            'sha256':digest,'backup':str(location.relative_to(root)),
            'source_commit':source_commit,'task_id':task,'timestamp_utc':stamp,
            'restoration_instruction':
                f"Restore exact bytes from {location.relative_to(root)} to {rel}; "
                f"verify SHA-256 {digest} before resuming work."}
    log=root/'.riverview-backups'/'manifest.jsonl'
    with log.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(record,sort_keys=True)+'\n')
    return record

def verified_predecessor(root, rel, old):
    log=root/'.riverview-backups'/'manifest.jsonl'
    if not log.is_file():
        return False
    for line in log.read_text(encoding='utf-8').splitlines():
        try:
            record=json.loads(line)
            if record.get('path')!=rel or record.get('sha256')!=old['sha256']:
                continue
            location=(root/record['backup']).resolve()
            if not location.is_relative_to((root/'.riverview-backups').resolve()):
                continue
            if location.is_file() and sha(location.read_bytes())==old['sha256']:
                return True
        except (ValueError, KeyError, OSError, json.JSONDecodeError):
            continue
    return False

def check(root, baseline):
    baseline_files={x['path']:x for x in json.loads(baseline.read_text())['files']}
    issues=[]
    for entry in inventory(root):
        rel=entry['path']
        if not entry['revision']:
            issues.append({'path':rel,'issue':'missing_revision'})
        old=baseline_files.get(rel)
        if old and old['sha256']!=entry['sha256']:
            initializes_legacy = old['revision'] is None and entry['revision'] == '1.0.0'
            if not initializes_legacy and not inc(old['revision'],entry['revision']):
                issues.append({'path':rel,'issue':'revision_not_incremented','baseline':old['revision'],'current':entry['revision']})
            if not verified_predecessor(root,rel,old):
                issues.append({'path':rel,'issue':'predecessor_backup_missing_or_invalid'})
    return issues

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default='.')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('inventory')
    b=sub.add_parser('backup'); b.add_argument('path'); b.add_argument('--task',required=True)
    c=sub.add_parser('check'); c.add_argument('--baseline',required=True)
    a=p.parse_args()
    root=Path(a.root).resolve()
    try:
        if a.cmd=='inventory': result={'files':inventory(root)}
        elif a.cmd=='backup': result=backup(root,a.path,a.task)
        else:
            issues=check(root,Path(a.baseline));result={'passed':not issues,'issues':issues}
        print(json.dumps(result,indent=2))
        if a.cmd=='check' and issues: return 1
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError,json.JSONDecodeError) as exc:
        print(json.dumps({'error':str(exc)}));return 2

if __name__=='__main__':
    sys.exit(main())

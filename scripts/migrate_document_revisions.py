# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/migrate_document_revisions.py
# Component: ENG-REVISION-CONTROL
# Revision: 1.0.2
# Purpose: Stage documentation revision migration from a preserved Git archive
# Execution Model: Request-driven, repeatable and non-destructive
# Observability: Machine-readable JSON report and exit status
# Dependencies: Python 3.10+, standard library
# Authority: Writes staging directory only, never production source
# Changed: 2026-10-09 UTC | ENG-REV-002 | Recognize heading revisions and reject ambiguity
# Contracts: docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md
# Tests: tests/test_migrate_document_revisions.py
# History: Git and predecessor archive
# =============================================================================
"""Create a staged, auditable documentation migration from a Git tar archive."""
import argparse
import hashlib
import io
import json
import re
import sys
import tarfile
from pathlib import Path

REV = re.compile(r'(?im)^\s*(?:\*\*)?\s*(?:Document Revision|File Revision|Revision)\s*(?:\*\*)?\s*:\s*(?:\*\*)?\s*(?:Rev\s+)?(\d+\.\d+(?:\.\d+)?)\b')
HEADING_REV = re.compile(r'(?im)^#{1,6}[^\n]*?\s[—–-]\sRev\s+(\d+\.\d+(?:\.\d+)?)\s*
BINARY_LIMIT = 100 * 1024 * 1024

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def migrate(archive, destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Destination must be absent or empty; no overwrites')
    destination.mkdir(parents=True, exist_ok=True)
    source = destination / 'original'
    staged = destination / 'staged'
    source.mkdir()
    staged.mkdir()
    rows = []
    with tarfile.open(archive, 'r:*') as tf:
        members = [m for m in tf.getmembers() if m.isfile() and m.name.endswith('.md')]
        for member in members:
            rel = Path(member.name)
            if rel.is_absolute() or '..' in rel.parts or member.size > BINARY_LIMIT:
                raise ValueError('Unsafe archive entry: ' + member.name)
            stream = tf.extractfile(member)
            if stream is None:
                raise ValueError('Missing member: ' + member.name)
            old = stream.read()
            if len(old) != member.size:
                raise ValueError('Incomplete archive entry: ' + member.name)
            text = old.decode('utf-8')
            matches = [m.group(1) for m in REV.finditer(text[:12000])]\n            matches += [m.group(1) for m in HEADING_REV.finditer(text[:12000])]\n            if len(matches) > 1:\n                raise ValueError('Ambiguous revision identifiers: ' + member.name)\n            found = matches[0] if matches else None
            # Existing legacy Rev X.Y metadata is preserved, not rewritten.
            if found:
                new = old
                rev = found
                action = 'already_revisioned'
            else:
                rev = '1.0.0'
                header = ('<!--\nRiverview~ Controlled Document\nFile: ' + member.name +
                          '\nRevision: ' + rev + '\nMigration: ENG-REV-002\n-->\n')
                new = (header + text).encode('utf-8')
                action = 'added_revision_header'
            prior = source / rel
            output = staged / rel
            prior.parent.mkdir(parents=True, exist_ok=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            prior.write_bytes(old)
            output.write_bytes(new)
            # Byte-exact predecessor and deterministic change verification.
            if prior.read_bytes() != old or output.read_bytes() != new:
                raise RuntimeError('Write verification failed: ' + member.name)
            if action == 'added_revision_header' and not new.endswith(old):
                raise RuntimeError('Substantive content changed: ' + member.name)
            rows.append({'path':member.name,'revision':rev,'action':action,
                         'original_sha256':digest(old),'staged_sha256':digest(new),
                         'original_bytes':len(old),'staged_bytes':len(new)})
    report={'status':'PASS','source_archive':str(archive),'staging_root':str(destination),
            'documents':len(rows),'changed':sum(x['action']=='added_revision_header' for x in rows),
            'unchanged':sum(x['action']=='already_revisioned' for x in rows),
            'files':rows}
    (destination/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    args=parser.parse_args()
    try:
        result=migrate(args.archive.resolve(),args.destination.resolve())
        print(json.dumps(result,indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, UnicodeError, tarfile.TarError) as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)}))
        return 1

if __name__=='__main__':
    sys.exit(main())
)
BINARY_LIMIT = 100 * 1024 * 1024

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def migrate(archive, destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Destination must be absent or empty; no overwrites')
    destination.mkdir(parents=True, exist_ok=True)
    source = destination / 'original'
    staged = destination / 'staged'
    source.mkdir()
    staged.mkdir()
    rows = []
    with tarfile.open(archive, 'r:*') as tf:
        members = [m for m in tf.getmembers() if m.isfile() and m.name.endswith('.md')]
        for member in members:
            rel = Path(member.name)
            if rel.is_absolute() or '..' in rel.parts or member.size > BINARY_LIMIT:
                raise ValueError('Unsafe archive entry: ' + member.name)
            stream = tf.extractfile(member)
            if stream is None:
                raise ValueError('Missing member: ' + member.name)
            old = stream.read()
            if len(old) != member.size:
                raise ValueError('Incomplete archive entry: ' + member.name)
            text = old.decode('utf-8')
            found = REV.search(text[:12000])
            # Existing legacy Rev X.Y metadata is preserved, not rewritten.
            if found:
                new = old
                rev = found.group(1)
                action = 'already_revisioned'
            else:
                rev = '1.0.0'
                header = ('<!--\nRiverview~ Controlled Document\nFile: ' + member.name +
                          '\nRevision: ' + rev + '\nMigration: ENG-REV-002\n-->\n')
                new = (header + text).encode('utf-8')
                action = 'added_revision_header'
            prior = source / rel
            output = staged / rel
            prior.parent.mkdir(parents=True, exist_ok=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            prior.write_bytes(old)
            output.write_bytes(new)
            # Byte-exact predecessor and deterministic change verification.
            if prior.read_bytes() != old or output.read_bytes() != new:
                raise RuntimeError('Write verification failed: ' + member.name)
            if action == 'added_revision_header' and not new.endswith(old):
                raise RuntimeError('Substantive content changed: ' + member.name)
            rows.append({'path':member.name,'revision':rev,'action':action,
                         'original_sha256':digest(old),'staged_sha256':digest(new),
                         'original_bytes':len(old),'staged_bytes':len(new)})
    report={'status':'PASS','source_archive':str(archive),'staging_root':str(destination),
            'documents':len(rows),'changed':sum(x['action']=='added_revision_header' for x in rows),
            'unchanged':sum(x['action']=='already_revisioned' for x in rows),
            'files':rows}
    (destination/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    args=parser.parse_args()
    try:
        result=migrate(args.archive.resolve(),args.destination.resolve())
        print(json.dumps(result,indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, UnicodeError, tarfile.TarError) as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)}))
        return 1

if __name__=='__main__':
    sys.exit(main())

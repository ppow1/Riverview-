# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/build_camrui_package.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.4
# Purpose: Build a self-contained package from an exact committed Git revision
# Execution Model: Request-driven engineering utility
# Observability: Source commit, file checksums and archive SHA-256
# Dependencies: Python 3, Git
# Authority: Writes an absent output outside checkout; excludes credentials, Git metadata and predecessor archives
# Changed: 2026-10-13 UTC | RV-M1.1-PACKAGE-BASH-001 | Allow one reviewed Bash runner by exact path and shebang
# Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PACKAGING | Exclude tracked .riverview-backups artifacts from release archives
# Changed: 2026-10-19 UTC | RV-W3-INTEGRATED-RELEASE-BLOCKER-RESOLUTION | Pin gzip metadata for reproducible full-source release archives.
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: docs/history/RV-M1.1-002/rev1.0.0/scripts/build_camrui_package.py
import argparse
import hashlib
from gzip import GzipFile
import io
from pathlib import Path
import subprocess
import tarfile


BASH_SHELL_ALLOWLIST = {
    "scripts/run_supervised_grace_execution.sh": b"#!/usr/bin/env bash\n",
}


def validate_shell(name, content):
    """Validate exact supported interpreters and reject unsafe shell bytes."""
    if name.endswith(".sh"):
        expected_shebang = BASH_SHELL_ALLOWLIST.get(name, b"#!/bin/sh\n")
        if (not content.startswith(expected_shebang) or not content.endswith(b"\n")
                or b"\r" in content or b"\x00" in content):
            interpreter = "authorized Bash" if name in BASH_SHELL_ALLOWLIST else "POSIX /bin/sh"
            raise ValueError("Linux shell requires an LF-only " + interpreter + " script without BOM/NUL: " + name)
        return "bash" if name in BASH_SHELL_ALLOWLIST else "sh"
    return None


def committed_files(root, commit):
    # git archive uses convert_to_working_tree(), including core.autocrlf on
    # Windows. Read blob objects instead: neither checkout settings nor export
    # attributes may change the bytes associated with SOURCE_COMMIT.
    tree = subprocess.check_output(["git", "-C", str(root), "ls-tree", "-r", "-z", "--full-tree", commit])
    entries = []
    for record in tree.split(b"\x00"):
        if not record:
            continue
        metadata, name_bytes = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        name = name_bytes.decode("utf-8")
        if name.startswith(".riverview-backups/"):
            continue
        if mode not in (b"100644", b"100755") or kind != b"blob":
            raise ValueError("Only regular committed files may be packaged: " + name)
        if Path(name).is_absolute() or ".." in Path(name).parts or "\n" in name or "\r" in name or "\\" in name:
            raise ValueError("Unsupported manifest filename")
        if name in ("SOURCE_COMMIT", "PACKAGE_SHA256SUMS"):
            raise ValueError("Reserved package metadata filename")
        entries.append((name, oid, int(mode, 8) & 0o777))
    # One batch keeps this practical on Windows while retaining exact blob bytes.
    blobs = subprocess.check_output(["git", "-C", str(root), "cat-file", "--batch"],
                                    input=b"".join(oid + b"\n" for _, oid, _ in entries))
    stream = io.BytesIO(blobs)
    files = []
    for name, oid, mode in entries:
        header = stream.readline().split()
        if len(header) != 3 or header[:2] != [oid, b"blob"]:
            raise ValueError("Unexpected Git blob response")
        size = int(header[2])
        content = stream.read(size)
        if len(content) != size or stream.read(1) != b"\n":
            raise ValueError("Truncated Git blob response")
        validate_shell(name, content)
        files.append((name, content, mode))
    if stream.read():
        raise ValueError("Unexpected trailing Git blob data")
    return files


def build(root, output):
    root, output = root.resolve(), output.resolve()
    if output.is_relative_to(root):
        raise ValueError("Package output must be outside the checkout")
    subprocess.run(["git", "-C", str(root), "diff", "--exit-code", "HEAD"], check=True, capture_output=True)
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    checksums = []
    files = committed_files(root, commit)
    files.append(("SOURCE_COMMIT", (commit + "\n").encode(), 0o644))
    for name, content, _ in files:
        checksums.append(hashlib.sha256(content).hexdigest() + "  " + name)
    files.append(("PACKAGE_SHA256SUMS", ("\n".join(checksums) + "\n").encode(), 0o644))
    with output.open("xb") as target:
        with GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for name, content, mode in files:
                    member = tarfile.TarInfo(name)
                    member.size, member.mode = len(content), mode
                    archive.addfile(member, io.BytesIO(content))
    return commit, hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    commit, digest = build(Path(__file__).resolve().parents[1], args.output)
    print("source_commit=" + commit)
    print("archive_sha256=" + digest)

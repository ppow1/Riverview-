# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/build_camrui_package.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Build a self-contained package from an exact committed Git revision
# Execution Model: Request-driven engineering utility
# Observability: Source commit, file checksums and archive SHA-256
# Dependencies: Python 3, Git
# Authority: Writes an absent output outside checkout; excludes credentials and Git metadata
# Changed: 2026-10-10 UTC | RV-M1.1-001 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: New file; no predecessor; Git
import argparse
import hashlib
import io
from pathlib import Path
import subprocess
import tarfile


def build(root, output):
    root, output = root.resolve(), output.resolve()
    if output.is_relative_to(root):
        raise ValueError("Package output must be outside the checkout")
    subprocess.run(["git", "-C", str(root), "diff", "--exit-code", "HEAD"], check=True, capture_output=True)
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    raw = subprocess.check_output(["git", "-C", str(root), "archive", "--format=tar", commit])
    checksums = []
    files = []
    with tarfile.open(fileobj=io.BytesIO(raw)) as source:
        for member in source:
            if member.isdir():
                continue
            if not member.isfile() or Path(member.name).is_absolute() or ".." in Path(member.name).parts:
                raise ValueError("Only regular relative files may be packaged")
            if "\n" in member.name or "\\" in member.name:
                raise ValueError("Unsupported manifest filename")
            content = source.extractfile(member).read()
            files.append((member.name, content, member.mode))
    files.append(("SOURCE_COMMIT", (commit + "\n").encode(), 0o644))
    for name, content, _ in files:
        checksums.append(hashlib.sha256(content).hexdigest() + "  " + name)
    files.append(("PACKAGE_SHA256SUMS", ("\n".join(checksums) + "\n").encode(), 0o644))
    with output.open("xb") as target:
        with tarfile.open(fileobj=target, mode="w:gz") as archive:
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

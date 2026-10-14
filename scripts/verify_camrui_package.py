# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_camrui_package.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.1
# Purpose: Inspect actual archive bytes and checksums before Linux deployment
# Execution Model: Request-driven read-only engineering diagnostic
# Observability: rv.package-verification.v1 JSON, shell hashes, CR/BOM counts and line-15 hex
# Dependencies: Python 3.10+ standard library; works on Windows without a Linux shell
# Authority: Reads named package only; never extracts, executes or edits host files
# Changed: 2026-10-13 UTC | RV-M1.1-PACKAGE-BASH-001 | Verify interpreter policy for every packaged shell script
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py
# History: New file; no predecessor
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

from build_camrui_package import validate_shell


def verify(path):
    report = dict(projection_version="rv.package-verification.v1",
                  archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  source_commit=None, manifest="FAIL", shell_compatibility="FAIL", shells=[])
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or any(not member.isfile() for member in members):
            raise ValueError("Package must contain unique regular files")
        report["source_commit"] = archive.extractfile("SOURCE_COMMIT").read().decode().strip()
        manifest = archive.extractfile("PACKAGE_SHA256SUMS").read().decode().splitlines()
        manifested = set()
        for line in manifest:
            digest, name = line.split("  ", 1)
            if name in manifested or digest != hashlib.sha256(archive.extractfile(name).read()).hexdigest():
                raise ValueError("Manifest checksum mismatch or duplicate")
            manifested.add(name)
        if manifested != set(names) - {"PACKAGE_SHA256SUMS"}:
            raise ValueError("Manifest membership mismatch")
        report["manifest"] = "PASS"
        valid = True
        shell_names = sorted(name for name in names if name.endswith(".sh"))
        for name in shell_names:
            content = archive.extractfile(name).read()
            lines = content.splitlines(keepends=True)
            entry = dict(path=name, sha256=hashlib.sha256(content).hexdigest(),
                         cr_bytes=content.count(b"\r"), crlf_pairs=content.count(b"\r\n"),
                         utf8_bom=content.startswith(b"\xef\xbb\xbf"), nul_bytes=content.count(b"\x00"),
                         line_15_hex=lines[14].hex() if len(lines) >= 15 else None, compatible=True)
            try:
                entry["interpreter"] = validate_shell(name, content)
            except ValueError:
                entry["compatible"] = False
                valid = False
            report["shells"].append(entry)
        report["shell_compatibility"] = "PASS" if valid else "FAIL"
    return report, 0 if valid else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        report, code = verify(args.archive)
    except (OSError, ValueError, KeyError, UnicodeError, tarfile.TarError):
        report, code = {"projection_version": "rv.package-verification.v1",
                        "status": "unavailable", "error_code": "INVALID_PACKAGE"}, 2
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(code)

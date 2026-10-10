#!/usr/bin/python3 -I
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/riverview_privctl.py
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Narrow privileged broker for approved New Riverview deployment operations
# Execution Model: Request-driven root-owned fixed-operation CLI
# Observability: Structured JSON outcomes and systemd status
# Dependencies: Python 3.10+, tarfile, systemd, root-owned package policy
# Authority: One fixed service, validated releases, protected package policy; no shell input
# Changed: 2026-10-10 UTC | RV-M1.1-009 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_privctl.py
# History: Git + .riverview-backups/manifest.jsonl
# =============================================================================
"""Root-owned fixed-operation deployment broker; never executes caller-provided code."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import io
import re
import stat
import subprocess
import sys
import tarfile
from datetime import datetime, timezone

POLICY = Path("/etc/riverview-privctl.json")
PACKAGES = Path("/var/lib/riverview-privctl/packages")
RELEASES = Path("/opt/riverview/releases")
ACTIVE = Path("/opt/riverview-core")
UNIT = "riverview-baseline.service"
BACKUPS = Path("/var/backups")
MAX_FILES = 5000
MAX_BYTES = 100 * 1024 * 1024
PACKAGE_ID = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")
BACKUP_ID = re.compile(r"riverview-baseline\.[A-Za-z0-9]{8,32}\Z")
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"}
VENV_SYMLINKS = {".venv/lib64": "lib", ".venv/bin/python": "python3",
                 ".venv/bin/python3.12": "python3", ".venv/bin/python3": "/usr/bin/python3"}


class BrokerError(Exception):
    """Request rejected without attempting a privileged side effect."""


class BrokerParser(argparse.ArgumentParser):
    def error(self, message):
        # Never reflect caller-supplied arguments into privileged diagnostics.
        self.exit(2, "riverview-privctl: invalid request\n")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_regular(path, owner=0, max_mode=0o022):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != owner or info.st_mode & max_mode:
        raise BrokerError("unsafe_file_metadata")
    return info


def read_policy(path=POLICY):
    safe_regular(path, owner=0, max_mode=0o077)
    if stat.S_IMODE(path.lstat().st_mode) != 0o600:
        raise BrokerError("unsafe_policy_mode")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BrokerError("invalid_policy") from exc
    if (not isinstance(policy, dict) or policy.get("format") != "rv.privctl-policy.v1" or
            not isinstance(policy.get("packages"), dict)):
        raise BrokerError("invalid_policy")
    return policy


def validated_members(archive_bytes, expected_digest, expected_commit):
    """Verify exact approved archive, then parse bounded regular members only."""
    if sha(archive_bytes) != expected_digest:
        raise BrokerError("package_digest_mismatch")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            members, seen, total = [], set(), 0
            for member in archive.getmembers():
                name = member.name
                rel = PurePosixPath(name)
                if (not member.isfile() or rel.is_absolute() or str(rel) != name or not name or
                        any(part in ("", ".", "..") for part in rel.parts) or
                        "\\" in name or "\n" in name or "\r" in name or name in seen):
                    raise BrokerError("unsafe_package_member")
                if len(members) >= MAX_FILES:
                    raise BrokerError("package_file_limit")
                total += member.size
                if total > MAX_BYTES:
                    raise BrokerError("package_size_limit")
                seen.add(name)
                stream = archive.extractfile(member)
                if stream is None:
                    raise BrokerError("invalid_package_member")
                content = stream.read(member.size + 1)
                if len(content) != member.size:
                    raise BrokerError("truncated_package_member")
                members.append((name, content, member.mode & 0o777))
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise BrokerError("invalid_package_archive") from exc
    by_name = {name: data for name, data, _ in members}
    if by_name.get("SOURCE_COMMIT", b"").decode("ascii", "ignore").strip() != expected_commit:
        raise BrokerError("package_commit_mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise BrokerError("invalid_approved_commit")
    checksums = by_name.get("PACKAGE_SHA256SUMS")
    if checksums is None:
        raise BrokerError("package_manifest_missing")
    expected = {}
    try:
        for line in checksums.decode("ascii").splitlines():
            digest, name = line.split("  ", 1)
            if not re.fullmatch(r"[0-9a-f]{64}", digest) or name in expected:
                raise ValueError
            expected[name] = digest
    except (UnicodeError, ValueError):
        raise BrokerError("invalid_package_manifest")
    actual_names = set(by_name) - {"PACKAGE_SHA256SUMS"}
    if set(expected) != actual_names or any(sha(by_name[name]) != digest for name, digest in expected.items()):
        raise BrokerError("package_manifest_mismatch")
    for required in ("deploy/install_baseline.sh", "deploy/rollback_baseline.sh",
                     "deploy/systemd/riverview-baseline.service", "scripts/capture_baseline_acceptance.py"):
        if required not in by_name:
            raise BrokerError("required_package_file_missing")
    return members


def _root_owned_tree(path):
    if path.is_symlink() or not path.is_dir() or path.stat().st_uid != 0:
        raise BrokerError("unsafe_release_directory")
    if path.stat().st_mode & 0o022:
        raise BrokerError("writable_release_directory")
    for item in path.rglob("*"):
        info = item.lstat()
        if info.st_uid != 0:
            raise BrokerError("unsafe_release_content")
        if stat.S_ISLNK(info.st_mode):
            validate_release_symlink(path, item)
            continue
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise BrokerError("unsafe_release_content")
        if info.st_mode & 0o022:
            raise BrokerError("writable_release_content")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise BrokerError("hardlinked_release_content")


def validate_release_symlink(release, path):
    rel = path.relative_to(release).as_posix()
    expected = VENV_SYMLINKS.get(rel)
    if expected is None or os.readlink(path) != expected:
        raise BrokerError("unexpected_release_symlink")
    target = path.resolve(strict=True)
    if expected.startswith("/"):
        allowed = Path(expected).resolve(strict=True)
        if target != allowed:
            raise BrokerError("unsafe_release_symlink_target")
        info = target.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise BrokerError("unsafe_release_symlink_target")
    elif rel == ".venv/lib64":
        if not target.is_relative_to(release.resolve(strict=True)):
            raise BrokerError("release_symlink_escapes_release")
    elif target != Path("/usr/bin/python3").resolve(strict=True):
        raise BrokerError("unsafe_release_symlink_target")


def validate_active_predecessor():
    if not ACTIVE.exists() and not ACTIVE.is_symlink():
        return
    if not ACTIVE.is_symlink():
        raise BrokerError("active_deployment_not_symlink")
    target = ACTIVE.resolve(strict=True)
    if (not target.is_relative_to(RELEASES.resolve(strict=True)) or
            not re.fullmatch(r"[0-9a-f]{40}", target.name)):
        raise BrokerError("unsafe_active_predecessor")
    _root_owned_tree(target)


def ensure_release_parent(releases_dir):
    """Create/validate only the fixed /opt/riverview deployment directories."""
    expected = Path("/opt/riverview/releases")
    if releases_dir != expected:
        raise BrokerError("unexpected_release_root")
    for directory in (Path("/opt"), Path("/opt/riverview"), expected):
        if directory.exists() or directory.is_symlink():
            info = directory.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or
                    info.st_mode & 0o022):
                raise BrokerError("unsafe_release_parent")
        else:
            directory.mkdir(mode=0o755)


def validate_rollback_record(record):
    for child in record.iterdir():
        info = child.lstat()
        if info.st_uid != 0:
            raise BrokerError("unsafe_rollback_content")
        if child.name in {"previous.service", "SHA256SUMS", "previous.release", "installed.commit"}:
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
                raise BrokerError("unsafe_rollback_content")
        elif child.name == "new-link":
            if not stat.S_ISLNK(info.st_mode) or os.readlink(child) != str(RELEASES / child.parent.joinpath("installed.commit").read_text().strip()):
                raise BrokerError("unsafe_rollback_content")
        elif child.name == "restore-link":
            raise BrokerError("incomplete_rollback_record")
        else:
            raise BrokerError("unexpected_rollback_content")
    previous = record / "previous.release"
    if previous.exists():
        target_text = previous.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"/opt/riverview/releases/[0-9a-f]{40}", target_text):
            raise BrokerError("unsafe_previous_release")
        target = Path(target_text)
        _root_owned_tree(target)


def install_package(package_id, policy_path=POLICY, packages_dir=PACKAGES, releases_dir=RELEASES,
                    runner=subprocess.run):
    if not PACKAGE_ID.fullmatch(package_id):
        raise BrokerError("invalid_package_id")
    policy = read_policy(policy_path)
    approved = policy["packages"].get(package_id)
    if not isinstance(approved, dict):
        raise BrokerError("package_not_approved")
    digest, commit = approved.get("sha256"), approved.get("source_commit")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise BrokerError("invalid_approved_digest")
    package_path = packages_dir / (package_id + ".tar.gz")
    safe_regular(package_path, owner=0, max_mode=0o077)
    if stat.S_IMODE(package_path.lstat().st_mode) != 0o400:
        raise BrokerError("unsafe_package_mode")
    blob = package_path.read_bytes()
    members = validated_members(blob, digest, commit)
    validate_active_predecessor()
    release = releases_dir / commit
    ensure_release_parent(releases_dir)
    if release.exists() or release.is_symlink():
        _root_owned_tree(release)
    else:
        release.mkdir(mode=0o755)
    # Resume only exact, safe partial extraction; never overwrite a conflicting file.
    for name, content, mode in members:
        target = release.joinpath(*PurePosixPath(name).parts)
        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        cursor = release
        for part in PurePosixPath(name).parts[:-1]:
            cursor = cursor / part
            if cursor.is_symlink() or not cursor.is_dir() or cursor.stat().st_uid != 0:
                raise BrokerError("unsafe_release_parent")
        if target.exists() or target.is_symlink():
            info = target.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or target.read_bytes() != content:
                raise BrokerError("release_content_conflict")
            continue
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode & 0o755 or 0o644)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.chown(target, 0, 0)
        os.chmod(target, mode & 0o755 or 0o644)
    _root_owned_tree(release)
    runner(["/bin/sh", str(release / "deploy/install_baseline.sh")], cwd=release,
           env=dict(SAFE_ENV), check=True, timeout=900)
    _root_owned_tree(release)
    return {"operation": "deploy", "source_commit": commit, "result": "installer_completed"}


def service(action, runner=subprocess.run):
    if action not in {"start", "stop", "restart", "status"}:
        raise BrokerError("invalid_service_action")
    command = ["/usr/bin/systemctl", action, UNIT]
    result = runner(command, env=dict(SAFE_ENV), check=False, timeout=60,
                    text=True, capture_output=True)
    return {"operation": "service", "action": action, "exit_code": result.returncode,
            "stdout": (result.stdout or "")[-4000:], "stderr": (result.stderr or "")[-2000:]}


def trusted_active_release():
    if not ACTIVE.is_symlink():
        raise BrokerError("active_release_missing")
    target = ACTIVE.resolve(strict=True)
    if not target.is_relative_to(RELEASES.resolve(strict=True)):
        raise BrokerError("active_release_outside_root")
    _root_owned_tree(target)
    return target


def acceptance(runner=subprocess.run):
    release = trusted_active_release()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = Path("/var/lib/riverview") / ("acceptance-" + stamp + ".json")
    result = runner(["/usr/bin/python3", str(release / "scripts/capture_baseline_acceptance.py"),
                     "--output", str(output)], cwd=release, env=dict(SAFE_ENV), check=False,
                    timeout=180, text=True, capture_output=True)
    return {"operation": "acceptance", "evidence": str(output), "exit_code": result.returncode,
            "output": (result.stdout or "")[-1000:], "error": (result.stderr or "")[-1000:]}


def report(runner=subprocess.run):
    """Return the fixed sanitized report through its root-owned consumer."""
    release = trusted_active_release()
    reader = release / "scripts/read_baseline_report.py"
    safe_regular(reader, owner=0, max_mode=0o022)
    result = runner(["/usr/bin/python3", str(reader)], cwd=release, env=dict(SAFE_ENV),
                    check=False, timeout=30, text=True, capture_output=True)
    try:
        snapshot = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise BrokerError("invalid_report_output") from exc
    return {"operation": "report", "exit_code": result.returncode, "snapshot": snapshot}


def rollback(record_id, runner=subprocess.run):
    if not BACKUP_ID.fullmatch(record_id):
        raise BrokerError("invalid_rollback_record")
    record = BACKUPS / record_id
    if record.is_symlink() or not record.is_dir() or record.stat().st_uid != 0 or stat.S_IMODE(record.stat().st_mode) != 0o700:
        raise BrokerError("unsafe_rollback_record")
    validate_rollback_record(record)
    release = trusted_active_release()
    script = release / "deploy/rollback_baseline.sh"
    safe_regular(script, owner=0, max_mode=0o022)
    runner(["/bin/sh", str(script), str(record)], cwd=release, env=dict(SAFE_ENV),
           check=True, timeout=120, text=True, capture_output=True)
    return {"operation": "rollback", "record_id": record_id, "result": "rollback_completed"}


def parse_args(argv=None):
    parser = BrokerParser(prog="riverview-privctl")
    sub = parser.add_subparsers(dest="operation", required=True)
    deploy = sub.add_parser("deploy"); deploy.add_argument("package_id")
    svc = sub.add_parser("service"); svc.add_argument("action", choices=("start", "stop", "restart", "status"))
    sub.add_parser("accept")
    sub.add_parser("report")
    rb = sub.add_parser("rollback"); rb.add_argument("record_id")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if os.geteuid() != 0:
        print("riverview-privctl: must be invoked through the authorized privilege policy", file=sys.stderr)
        return 2
    try:
        if args.operation == "deploy": result = install_package(args.package_id)
        elif args.operation == "service": result = service(args.action)
        elif args.operation == "accept": result = acceptance()
        elif args.operation == "report": result = report()
        else: result = rollback(args.record_id)
        print(json.dumps(result, sort_keys=True))
        return int(result.get("exit_code", 0))
    except (BrokerError, OSError, subprocess.SubprocessError) as exc:
        code = exc.args[0] if isinstance(exc, BrokerError) else type(exc).__name__
        print(json.dumps({"operation": args.operation, "result": "failed", "error": str(code)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

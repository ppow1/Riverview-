# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/browser_status_projection.py
# Component: LINUX-BROWSER-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Project local browser-run artifacts into a safe Steward-consumable status contract
# Execution Model: Request-driven local CLI/library
# Observability: Schema-validated JSON output and bounded stdout summary
# Dependencies: Python standard library; Git source commit supplied by caller
# Authority: Reads local evidence only; no browser, network, dashboard, or production access
# Changed: 2026-10-18 UTC | RV-C2-BROWSER-STATUS-001 | Require private output directory and validate evidence root
# Contracts: docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.md; docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.schema.json
# Tests: tests/test_browser_status_projection.py
# History: Git and revision/backup manifest
# =============================================================================
"""Create a lossy, privacy-safe status summary for local browser acceptance runs."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

FRESHNESS_TTL = timedelta(minutes=15)
DIAGNOSTIC_REF = "docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.md"
FAILURE_PRIORITY = (
    "blocked_non_get", "blocked_cross_origin", "browser_page_error",
    "browser_console_error", "request_failed",
)
ALLOWED_FAILURES = set(FAILURE_PRIORITY) | {
    "none", "assertion_failed", "runner_unavailable", "staging_target_unavailable",
    "unsupported_remote_target", "unknown",
}


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def _source_commit(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("source_commit_must_be_full_git_sha")
    return value


def _loopback_target(run_start: dict) -> bool:
    target = run_start.get("target_origin")
    if not isinstance(target, str):
        return False
    try:
        parts = urlsplit(target)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return False
        if parts.username or parts.password or parts.path not in {"", "/"} or parts.query or parts.fragment:
            return False
        host = parts.hostname.lower()
        if host == "localhost":
            return True
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _read_json(path: Path) -> dict | None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _safe_failure_category(evidence_dir: Path, errors: dict | None) -> str:
    if errors is None:
        return "runner_unavailable"
    kinds: set[str] = set()
    # Ignore report-provided filenames, messages, URLs, and test names. Only read
    # regular files in the selected evidence directory and retain fixed `kind` values.
    for path in sorted(evidence_dir.glob("*.errors.json"))[:200]:
        report = _read_json(path)
        if report is None or not isinstance(report.get("errors"), list):
            continue
        for item in report["errors"][:500]:
            if isinstance(item, dict) and item.get("kind") in ALLOWED_FAILURES:
                kinds.add(item["kind"])
    for kind in FAILURE_PRIORITY:
        if kind in kinds:
            return kind
    if errors.get("failed", 0):
        return "assertion_failed"
    return "unknown"


def _counts(errors: dict | None) -> dict[str, int]:
    result = {}
    for name in ("passed", "failed", "skipped"):
        value = errors.get(name, 0) if errors else 0
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            value = 0
        result[name] = value
    return result


def build_status(*, source_commit: str, observed_at: datetime | None = None,
                 run_start: dict | None = None, runner_result: dict | None = None,
                 errors: dict | None = None, evidence_dir: Path | None = None,
                 state: str | None = None) -> dict:
    """Build only allowlisted fields; caller-supplied state supports unavailable staging."""
    commit = _source_commit(source_commit)
    observed = observed_at or datetime.now(timezone.utc)
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("observed_at_must_be_timezone_aware")
    observed = observed.astimezone(timezone.utc)

    started = _timestamp(run_start.get("started_at")) if run_start else None
    completed = _timestamp(runner_result.get("completed_at")) if runner_result else None
    status = "unknown"
    environment = "unknown"
    category: str | None = "unknown"
    counts = _counts(errors)
    run_id: str | None = None
    activity = completed or started
    freshness = "unknown"

    if state in {"blocked", "staging_not_available"} and run_start is None:
        status = state
        category = "staging_target_unavailable" if state == "staging_not_available" else "unknown"
        environment = "staging" if state == "staging_not_available" else "unknown"
        freshness = "current"
    elif run_start is not None:
        if _loopback_target(run_start):
            environment = "local_loopback"
        else:
            status = "blocked"
            category = "unsupported_remote_target"
            environment = "unknown"
        if status != "blocked":
            mode = run_start.get("mode")
            if mode not in {"read-only-smoke", "grace-staging-readonly"}:
                status = "blocked"
                category = "unknown"
                environment = "unknown"
            elif started is None:
                status = "unknown"
                category = "unknown"
            else:
                digest = hashlib.sha256(f"{commit}\0{_iso(started)}".encode()).hexdigest()[:20]
                run_id = f"rvba-{digest}"
                if runner_result is None:
                    status = "running"
                    category = None
                elif runner_result.get("status") == "PASS" and runner_result.get("exit_code") == 0:
                    status = "passed"
                    category = "none"
                elif runner_result.get("status") == "FAIL" or runner_result.get("exit_code") not in (None, 0):
                    category = _safe_failure_category(evidence_dir or Path("."), errors)
                    status = ("blocked" if category in {"blocked_non_get", "blocked_cross_origin"}
                              else "failed")
                else:
                    status = "unknown"
                    category = "unknown"

    if activity:
        age = observed - activity
        if age < timedelta(0):
            freshness = "unknown"
        elif age <= FRESHNESS_TTL:
            freshness = "current"
        else:
            freshness = "stale"
    elif status in {"blocked", "staging_not_available"}:
        freshness = "current"
    elif status == "unknown":
        freshness = "unavailable"

    return {
        "schema_version": "rv.browser-acceptance.status.v1",
        "component_id": "LINUX-BROWSER-ACCEPTANCE",
        "source_commit": commit,
        "run_id": run_id,
        "environment": environment,
        "run_status": status,
        "failure_category": category if category in ALLOWED_FAILURES or category is None else "unknown",
        "observed_at": _iso(observed),
        "started_at": _iso(started),
        "completed_at": _iso(completed),
        "freshness": freshness,
        "counts": counts,
        "diagnostic_ref": DIAGNOSTIC_REF,
    }


def project_directory(evidence_dir: Path, *, source_commit: str,
                      observed_at: datetime | None = None) -> dict:
    if evidence_dir.is_symlink() or not evidence_dir.is_dir():
        raise ValueError("evidence_directory_must_be_real_directory")
    run_start = _read_json(evidence_dir / "run-start.json")
    runner_result = _read_json(evidence_dir / "runner-result.json")
    errors = _read_json(evidence_dir / "browser-errors.json")
    return build_status(source_commit=source_commit, observed_at=observed_at,
                        run_start=run_start, runner_result=runner_result,
                        errors=errors, evidence_dir=evidence_dir)


def write_status(path: Path, status: dict) -> None:
    # Never change permissions on a caller-selected existing directory. Requiring
    # a pre-created private directory prevents accidental chmod of shared paths.
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("status_output_parent_must_be_real_directory")
    if path.parent.stat().st_mode & 0o077:
        raise ValueError("status_output_parent_must_be_private")
    if path.is_symlink():
        raise ValueError("status_output_must_not_be_symlink")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(status, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True, help="full 40-character source commit SHA")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--state", choices=("blocked", "staging_not_available"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.evidence_dir:
        status = project_directory(args.evidence_dir, source_commit=args.source_commit)
    elif args.state:
        status = build_status(source_commit=args.source_commit, state=args.state)
    else:
        parser.error("provide --evidence-dir or an explicit unavailable --state")
    write_status(args.output, status)
    print(f"run_status={status['run_status']} freshness={status['freshness']} run_id={status['run_id'] or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

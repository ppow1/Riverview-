# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/poll_issue_assignments.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Purpose: Poll GitHub issue comments into an inert durable receipt cache
# Execution Model: Opt-in request-driven poll or explicitly started polling loop
# Observability: Sanitized JSON receipts and poll status on stdout
# Dependencies: Python 3.10+; GitHub CLI (`gh`) using caller-managed authentication
# Authority: Read-only GitHub issue access; receipts grant no assignment, execution, or session authority
# Changed: 2026-10-18 UTC | RV-W1-ISSUE-POLL-001 | Add opt-in issue comment discovery with idempotent local receipts.
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: tests/test_issue_assignment_poller.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Read issue comments as inert data and persist metadata-only discovery receipts."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode
from uuid import uuid4


_SCHEMA = "rv.issue-comment-receipts.v1"
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_LOCK_WAIT_SECONDS = 15.0
_LOCK_STALE_SECONDS = 300.0
_CURSOR_OVERLAP_SECONDS = 300
_MAX_BODY_BYTES = 2 * 1024 * 1024
_MAX_RECEIPT_FILE_BYTES = 32 * 1024 * 1024


class PollError(RuntimeError):
    """Sanitized poll, receipt, or persistence failure."""


def _now():
    return datetime.now(timezone.utc)


def _stamp(value):
    if value.tzinfo is None:
        raise ValueError("timestamp_timezone_required")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_stamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("timestamp_invalid") from None
    if parsed.tzinfo is None:
        raise ValueError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc)


def _validate_target(repository, issue_number):
    if not isinstance(repository, str) or not _REPO.fullmatch(repository) or ".." in repository:
        raise ValueError("repository_invalid")
    if type(issue_number) is not int or issue_number < 1:
        raise ValueError("issue_number_invalid")


def _gh_endpoint(repository, issue_number, since=None):
    _validate_target(repository, issue_number)
    endpoint = f"repos/{repository}/issues/{issue_number}/comments"
    query = {"per_page": 100}
    if since is not None:
        query["since"] = _stamp(since)
    return f"{endpoint}?{urlencode(query)}"


def fetch_issue_comments(repository, issue_number, since=None):
    """Use gh without a shell; response body text is returned only to the caller."""
    endpoint = _gh_endpoint(repository, issue_number, since)
    jq = ".[] | {id, html_url, user: .user.login, created_at, updated_at, body}"
    try:
        result = subprocess.run(
            ["gh", "api", "--paginate", "--jq", jq, endpoint],
            check=True, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60,
        )
    except FileNotFoundError:
        raise PollError("github_cli_unavailable") from None
    except subprocess.TimeoutExpired:
        raise PollError("github_api_timeout") from None
    except subprocess.CalledProcessError:
        # Do not echo GitHub CLI output; it may contain remote response details.
        raise PollError("github_api_failed") from None

    comments = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            comment = json.loads(line)
        except json.JSONDecodeError:
            raise PollError("github_api_response_invalid") from None
        if not isinstance(comment, dict):
            raise PollError("github_api_response_invalid")
        comments.append(comment)
    return comments


def _empty_state(repository, issue_number):
    return {"schema_version": _SCHEMA, "repository": repository,
            "issue_number": issue_number, "last_successful_poll_at": None,
            "cursor_updated_at": None,
            "comments": {}}


def _read_state(path, repository, issue_number):
    if path.is_symlink():
        raise PollError("receipt_path_symlink_rejected")
    if not path.exists():
        return _empty_state(repository, issue_number)
    try:
        if path.stat().st_size > _MAX_RECEIPT_FILE_BYTES:
            raise PollError("receipt_file_too_large")
        state = json.loads(path.read_text(encoding="utf-8"))
    except PollError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise PollError("receipt_file_invalid") from None
    if (not isinstance(state, dict) or state.get("schema_version") != _SCHEMA
            or state.get("repository") != repository
            or state.get("issue_number") != issue_number
            or not isinstance(state.get("comments"), dict)):
        raise PollError("receipt_contract_mismatch")
    for field in ("last_successful_poll_at", "cursor_updated_at"):
        if state.get(field) is not None:
            try:
                _parse_stamp(state[field])
            except ValueError:
                raise PollError("receipt_cursor_invalid") from None
    for identifier, record in state["comments"].items():
        if not isinstance(identifier, str) or not identifier.isdigit() or int(identifier) < 1:
            raise PollError("receipt_comment_id_invalid")
        expected_url = (f"https://github.com/{repository}/issues/{issue_number}"
                        f"#issuecomment-{identifier}")
        if (not isinstance(record, dict) or record.get("url") != expected_url
                or (record.get("author") is not None
                    and (not isinstance(record.get("author"), str)
                         or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", record["author"])))
                or not isinstance(record.get("versions"), list)
                or not record["versions"]):
            raise PollError("receipt_comment_record_invalid")
        try:
            _parse_stamp(record.get("created_at"))
            for version in record["versions"]:
                if (not isinstance(version, dict)
                        or not re.fullmatch(r"[0-9a-f]{64}",
                                            str(version.get("body_sha256", "")))):
                    raise ValueError("version_invalid")
                _parse_stamp(version.get("updated_at"))
                _parse_stamp(version.get("observed_at"))
        except (ValueError, TypeError):
            raise PollError("receipt_comment_version_invalid") from None
    return state


@contextmanager
def _state_lock(path, *, wait_seconds=_LOCK_WAIT_SECONDS,
                stale_seconds=_LOCK_STALE_SECONDS, sleep=time.sleep):
    lock = path.with_name(path.name + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            lock.mkdir()
        except FileExistsError:
            if lock.is_symlink():
                raise PollError("receipt_lock_symlink_rejected")
            try:
                age = time.time() - lock.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > stale_seconds:
                stale = lock.with_name(lock.name + ".stale-" + uuid4().hex)
                try:
                    lock.rename(stale)
                except (FileNotFoundError, FileExistsError, PermissionError):
                    continue
                shutil.rmtree(stale, ignore_errors=True)
                continue
            if time.monotonic() >= deadline:
                raise PollError("receipt_lock_timeout")
            sleep(0.01)
        except PermissionError:
            if time.monotonic() >= deadline:
                raise PollError("receipt_lock_unavailable") from None
            sleep(0.01)
        else:
            owner = {"token": token, "pid": os.getpid(),
                     "hostname": socket.gethostname(),
                     "acquired_at": _stamp(_now())}
            try:
                (lock / "owner.json").write_text(
                    json.dumps(owner, separators=(",", ":")), encoding="utf-8")
            except OSError:
                shutil.rmtree(lock, ignore_errors=True)
                raise PollError("receipt_lock_owner_write_failed") from None
            break
    try:
        yield
    finally:
        try:
            owner = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
            if owner.get("token") == token:
                shutil.rmtree(lock)
        except (OSError, ValueError, AttributeError):
            pass


def _write_atomic(path, state):
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(state, stream, ensure_ascii=True, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _receipt(comment, repository, issue_number, observed_at):
    if not isinstance(comment, dict):
        raise PollError("comment_invalid")
    identifier = comment.get("id")
    if type(identifier) is not int or identifier < 1:
        raise PollError("comment_id_invalid")
    expected_url = (f"https://github.com/{repository}/issues/{issue_number}"
                    f"#issuecomment-{identifier}")
    if comment.get("html_url") != expected_url:
        raise PollError("comment_url_invalid")
    author = comment.get("user")
    if author is not None and (not isinstance(author, str)
                               or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", author)):
        raise PollError("comment_author_invalid")
    body = comment.get("body")
    if not isinstance(body, str) or len(body.encode("utf-8")) > _MAX_BODY_BYTES:
        raise PollError("comment_body_invalid")
    try:
        created_at = _stamp(_parse_stamp(comment.get("created_at")))
        updated_at = _stamp(_parse_stamp(comment.get("updated_at")))
    except ValueError:
        raise PollError("comment_timestamp_invalid") from None
    return {"comment_id": str(identifier), "url": expected_url, "author": author,
            "created_at": created_at, "updated_at": updated_at,
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "observed_at": _stamp(observed_at)}


def poll_once(*, state_path: Path, repository="ppow1/Riverview-", issue_number=120,
              fetcher=fetch_issue_comments, now=_now, overlap_seconds=_CURSOR_OVERLAP_SECONDS,
              lock_options=None):
    """Fetch comments, then idempotently persist metadata-only receipts."""
    _validate_target(repository, issue_number)
    state_path = Path(state_path).expanduser().absolute()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if state_path.is_symlink():
        raise PollError("receipt_path_symlink_rejected")
    current = _read_state(state_path, repository, issue_number)
    since = None
    if current["cursor_updated_at"] is not None:
        since = _parse_stamp(current["cursor_updated_at"]) - timedelta(
            seconds=overlap_seconds)
    poll_started = now().astimezone(timezone.utc)
    try:
        comments = fetcher(repository, issue_number, since)
    except PollError:
        raise
    except Exception:
        raise PollError("github_fetch_failed") from None
    if not isinstance(comments, (list, tuple)):
        raise PollError("github_api_response_invalid")

    received = []
    for comment in comments:
        receipt = _receipt(comment, repository, issue_number, poll_started)
        received.append(receipt)

    options = lock_options or {}
    with _state_lock(state_path, **options):
        state = _read_state(state_path, repository, issue_number)
        changes = []
        for receipt in received:
            key = receipt["comment_id"]
            record = state["comments"].get(key)
            if record is None:
                state["comments"][key] = {
                    "url": receipt["url"], "author": receipt["author"],
                    "created_at": receipt["created_at"], "versions": [{
                        "updated_at": receipt["updated_at"],
                        "body_sha256": receipt["body_sha256"],
                        "observed_at": receipt["observed_at"],
                    }],
                }
                changes.append({"change": "discovered", **{
                    key: receipt[key] for key in (
                        "comment_id", "url", "author", "created_at", "updated_at", "body_sha256")}})
                continue
            if record.get("url") != receipt["url"] or record.get("author") != receipt["author"]:
                raise PollError("receipt_identity_conflict")
            versions = record.get("versions")
            if not isinstance(versions, list) or not versions:
                raise PollError("receipt_versions_invalid")
            if versions[-1].get("body_sha256") != receipt["body_sha256"]:
                versions.append({"updated_at": receipt["updated_at"],
                                 "body_sha256": receipt["body_sha256"],
                                 "observed_at": receipt["observed_at"]})
                record["versions"] = versions
                changes.append({"change": "edited", **{
                    key: receipt[key] for key in (
                        "comment_id", "url", "author", "created_at", "updated_at", "body_sha256")}})
        previous = state["last_successful_poll_at"]
        previous_time = _parse_stamp(previous) if previous is not None else None
        if previous_time is None or poll_started > previous_time:
            state["last_successful_poll_at"] = _stamp(poll_started)
        cursor = state["cursor_updated_at"]
        cursor_time = _parse_stamp(cursor) if cursor is not None else None
        remote_updates = [_parse_stamp(row["updated_at"]) for row in received]
        if remote_updates:
            newest = max(remote_updates)
            if cursor_time is None or newest > cursor_time:
                state["cursor_updated_at"] = _stamp(newest)
        _write_atomic(state_path, state)

    return {"ok": True, "repository": repository, "issue_number": issue_number,
            "observed_count": len(received), "receipt_changes": changes,
            "last_successful_poll_at": state["last_successful_poll_at"],
            "cursor_updated_at": state["cursor_updated_at"],
            "stored_comment_count": len(state["comments"])}


def watch(*, state_path, repository="ppow1/Riverview-", issue_number=120,
          interval_seconds=60, max_backoff_seconds=900, should_stop=lambda: False,
          sleep=time.sleep, poller=poll_once, on_result=lambda result: None,
          max_cycles=None):
    """Poll until explicitly stopped; use capped exponential backoff after failure."""
    if interval_seconds < 1 or max_backoff_seconds < interval_seconds:
        raise ValueError("poll_intervals_invalid")
    cycles = 0
    failures = 0
    while not should_stop() and (max_cycles is None or cycles < max_cycles):
        cycles += 1
        try:
            result = poller(state_path=state_path, repository=repository,
                            issue_number=issue_number)
            failures = 0
            on_result(result)
            delay = interval_seconds
        except PollError as exc:
            failures += 1
            delay = min(max_backoff_seconds,
                        interval_seconds * (2 ** min(failures - 1, 30)))
            on_result({"ok": False, "error": str(exc), "retry_in_seconds": delay})
        if max_cycles is None and should_stop():
            break
        if max_cycles is None or cycles < max_cycles:
            sleep(delay)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("poll-once", "watch"):
        command = sub.add_parser(name)
        command.add_argument("--state-file", type=Path, required=True,
                             help="Local receipt JSON path; no default shared/production path")
        command.add_argument("--repo", default="ppow1/Riverview-")
        command.add_argument("--issue", type=int, default=120)
    sub.choices["watch"].add_argument("--interval-seconds", type=int, default=60)
    sub.choices["watch"].add_argument("--max-backoff-seconds", type=int, default=900)
    args = parser.parse_args(argv)
    try:
        if args.command == "poll-once":
            result = poll_once(state_path=args.state_file, repository=args.repo,
                               issue_number=args.issue)
            print(json.dumps(result, sort_keys=True))
            return 0
        watch(state_path=args.state_file, repository=args.repo, issue_number=args.issue,
              interval_seconds=args.interval_seconds,
              max_backoff_seconds=args.max_backoff_seconds,
              on_result=lambda result: print(json.dumps(result, sort_keys=True), flush=True))
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, PollError) as exc:
        message = str(exc) if isinstance(exc, PollError) else "poll_configuration_or_storage_failed"
        print(json.dumps({"ok": False, "error": message}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

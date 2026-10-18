# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/work_registry.py
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Add one observational file-backed registry for workers, sessions, and work orders.
# Purpose: Persist cross-runtime work observations without dispatching or authorizing execution
# Execution Model: Request-driven library with process-safe file locking
# Observability: Versioned JSON snapshot consumed by the authenticated status dashboard
# Dependencies: Python standard library
# Authority: Registration is observability only; no work dispatch, resource allocation, or institutional grant
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: tests/test_work_registry.py
# =============================================================================
"""Durable, observational worker/session/work-order registry.

The registry intentionally does not claim that a live process or recent
heartbeat means an AI model is reasoning. Callers report activity explicitly.
All mutation uses a portable exclusive lock directory and atomic file replace;
readers see a complete old or new JSON document.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
import time
from uuid import uuid4


SCHEMA_VERSION = "rv.work-registry.v1"
_MAX_BYTES = 32 * 1024 * 1024
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_WORKER_TYPES = frozenset({"codex", "local_ai", "resident", "engineering",
                           "browser_test", "verification", "service", "other"})
_WORK_STATUSES = frozenset({"unknown", "queued", "active", "blocked",
                            "completed", "failed", "cancelled"})
_ACTIVITY = frozenset({"unknown", "idle", "working", "waiting"})
_MILESTONE_STATES = frozenset({"pending", "active", "blocked", "completed"})
_QUEUE_STATES = frozenset({"unknown", "queued", "dequeued", "running",
                           "completed", "failed"})
_SAFE_REF = re.compile(r"^[A-Za-z0-9._:/#?=&%+@-]{1,512}$")
_SENSITIVE_TEXT = re.compile(
    r"(?i)(?:bearer\s+\S+|(?:password|secret|api[_ -]?key|access[_ -]?token)\s*[:=]\s*\S+|"
    r"sk-[A-Za-z0-9_-]{12,}|chain[ -]of[ -]thought|(?:system|developer|user)\s+prompt|"
    r"private\s+(?:reasoning|thoughts?|trace))")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime | None = None) -> str:
    value = value or _now()
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_time(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _id(value, field):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{field} must be a bounded stable identifier")
    return value


def _text(value, field, *, maximum=512, nullable=True):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field} must be a nonempty string of at most {maximum} characters")
    if "\x00" in value or any(ord(char) < 32 and char not in "\t\n\r" for char in value):
        raise ValueError(f"{field} contains an invalid control character")
    if _SENSITIVE_TEXT.search(value):
        raise ValueError(f"{field} contains sensitive content")
    return value.strip()


def _reference(value, field, *, nullable=True):
    value = _text(value, field, maximum=512, nullable=nullable)
    if value is not None and not _SAFE_REF.fullmatch(value):
        raise ValueError(f"{field} must be a safe identifier or URL reference")
    return value


def _string_list(values, field, *, maximum=64):
    if not isinstance(values, (list, tuple)) or len(values) > maximum:
        raise ValueError(f"{field} must be a list with at most {maximum} entries")
    output = []
    for item in values:
        output.append(_text(item, field, maximum=256, nullable=False))
    if len(set(output)) != len(output):
        raise ValueError(f"{field} entries must be unique")
    return output


def _empty():
    return {"schema_version": SCHEMA_VERSION, "workers": {},
            "sessions": {}, "work_orders": {}}


class WorkRegistryError(RuntimeError):
    """Sanitized registry persistence or validation failure."""


class WorkRegistry:
    """Atomically persist observable workers, execution sessions, and tasks."""

    LOCK_WAIT_SECONDS = 15.0
    LOCK_STALE_SECONDS = 300.0

    def __init__(self, path: str | Path, *, stale_after_seconds: int = 90):
        if type(stale_after_seconds) is not int or stale_after_seconds < 1:
            raise ValueError("stale_after_seconds must be a positive integer")
        self.path = Path(path).expanduser().resolve()
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.stale_after_seconds = stale_after_seconds

    @contextmanager
    def _lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        token = uuid4().hex
        deadline = time.monotonic() + self.LOCK_WAIT_SECONDS
        while True:
            try:
                self.lock_path.mkdir()
                owner = {"token": token, "pid": os.getpid(),
                         "host": socket.gethostname(), "acquired_at": _stamp()}
                (self.lock_path / "owner.json").write_text(
                    json.dumps(owner, separators=(",", ":")), encoding="utf-8")
                break
            except (FileExistsError, PermissionError):
                if not self.lock_path.is_dir():
                    if not self.lock_path.exists():
                        continue
                    if time.monotonic() >= deadline:
                        raise WorkRegistryError("registry_lock_unavailable") from None
                    time.sleep(0.01)
                    continue
                try:
                    lock_age = time.time() - self.lock_path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if lock_age > self.LOCK_STALE_SECONDS:
                    stale = self.lock_path.with_name(
                        self.lock_path.name + ".stale-" + uuid4().hex)
                    try:
                        self.lock_path.rename(stale)
                    except (FileNotFoundError, FileExistsError, PermissionError):
                        continue
                    shutil.rmtree(stale, ignore_errors=True)
                    continue
                if time.monotonic() >= deadline:
                    raise WorkRegistryError("registry_lock_timeout")
                time.sleep(0.01)
        try:
            yield
        finally:
            try:
                owner = json.loads((self.lock_path / "owner.json").read_text(encoding="utf-8"))
                if owner.get("token") == token:
                    shutil.rmtree(self.lock_path)
            except (OSError, ValueError, AttributeError):
                pass

    def _read_unlocked(self):
        if self.path.is_symlink():
            raise WorkRegistryError("registry_path_symlink_rejected")
        if not self.path.exists():
            return _empty()
        try:
            if self.path.stat().st_size > _MAX_BYTES:
                raise WorkRegistryError("registry_file_too_large")
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except WorkRegistryError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise WorkRegistryError("registry_unreadable_or_invalid") from None
        if (not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION
                or not all(isinstance(document.get(name), dict)
                           for name in ("workers", "sessions", "work_orders"))):
            raise WorkRegistryError("registry_contract_invalid")
        return document

    def _write_unlocked(self, document):
        encoded = (json.dumps(document, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > _MAX_BYTES:
            raise WorkRegistryError("registry_file_too_large")
        handle, temporary_name = tempfile.mkstemp(
            prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, self.path)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass

    @staticmethod
    def _validate_worker(worker):
        if not isinstance(worker, dict):
            raise ValueError("worker record must be an object")
        _id(worker.get("worker_id"), "worker_id")
        if worker.get("worker_type") not in _WORKER_TYPES:
            raise ValueError("worker_type is unsupported")
        _text(worker.get("hostname"), "hostname", maximum=255, nullable=False)
        _text(worker.get("os"), "os", maximum=64, nullable=False)
        _string_list(worker.get("capabilities"), "capabilities")
        _text(worker.get("model_identity"), "model_identity", maximum=256)
        _reference(worker.get("endpoint_ref"), "endpoint_ref")
        _parse_time(worker.get("registered_at"))
        if set(worker) != {"worker_id", "worker_type", "hostname", "os", "capabilities",
                           "model_identity", "endpoint_ref", "registered_at"}:
            raise ValueError("worker record contains unsupported fields")

    @staticmethod
    def _validate_session(session):
        if not isinstance(session, dict):
            raise ValueError("session record must be an object")
        _id(session.get("session_id"), "session_id")
        _id(session.get("worker_id"), "worker_id")
        if session.get("lifecycle") not in {"unknown", "running", "completed", "disconnected"}:
            raise ValueError("session lifecycle is unsupported")
        if session.get("activity_state") not in _ACTIVITY:
            raise ValueError("session activity_state is unsupported")
        for key, maximum in (("hostname", 255), ("os", 64), ("repository", 512),
                             ("branch", 256), ("pull_request", 512),
                             ("model_identity", 256), ("endpoint_ref", 512)):
            if key in {"pull_request", "model_identity", "endpoint_ref"}:
                _reference(session.get(key), key)
            else:
                _text(session.get(key), key, maximum=maximum)
        for key in ("started_at", "last_heartbeat_at", "last_activity_at", "ended_at"):
            _parse_time(session.get(key))
        _id(session.get("session_id"), "session_id")
        if set(session) != {"session_id", "worker_id", "hostname", "os", "repository",
                "branch", "pull_request", "model_identity", "endpoint_ref", "lifecycle",
                "activity_state", "current_work_order_id", "started_at",
                "last_heartbeat_at", "last_activity_at", "ended_at"}:
            raise ValueError("session record contains unsupported fields")
        if session["current_work_order_id"] is not None:
            _id(session["current_work_order_id"], "current_work_order_id")

    @staticmethod
    def _validate_work_order(work):
        if not isinstance(work, dict):
            raise ValueError("work_order record must be an object")
        _id(work.get("work_order_id"), "work_order_id")
        if work.get("session_id") is not None:
            _id(work.get("session_id"), "session_id")
        if work.get("worker_id") is not None:
            _id(work.get("worker_id"), "worker_id")
        if work.get("ownership_state") not in {"unassigned", "proposed", "assigned", "acknowledged"}:
            raise ValueError("ownership_state is unsupported")
        _text(work.get("owner_label"), "owner_label", maximum=255)
        if work["ownership_state"] == "unassigned" and (work["worker_id"] is not None or work["owner_label"] is not None):
            raise ValueError("unassigned work cannot name an owner")
        if work["ownership_state"] == "proposed" and work["owner_label"] is None:
            raise ValueError("proposed ownership requires an owner label")
        if work["ownership_state"] in {"assigned", "acknowledged"} and work["worker_id"] is None:
            raise ValueError("assigned work requires a registered worker identity")
        if work.get("status") not in _WORK_STATUSES:
            raise ValueError("work-order status is unsupported")
        _text(work.get("title"), "title", maximum=160, nullable=False)
        for key, maximum in (("detail", 2000), ("blocker", 2000), ("next_action", 1000),
                             ("outcome", 2000), ("repository", 512), ("branch", 256),
                             ("pull_request", 512), ("deliverable", 512)):
            if key in {"pull_request", "deliverable"}:
                _reference(work.get(key), key)
            else:
                _text(work.get(key), key, maximum=maximum)
        _string_list(work.get("dependencies"), "dependencies")
        _string_list(work.get("evidence"), "evidence")
        milestones = work.get("milestones")
        if not isinstance(milestones, list) or len(milestones) > 100:
            raise ValueError("milestones must be a bounded list")
        for milestone in milestones:
            if (not isinstance(milestone, dict)
                    or set(milestone) != {"milestone_id", "title", "status"}
                    or milestone.get("status") not in _MILESTONE_STATES):
                raise ValueError("milestone record is invalid")
            _id(milestone["milestone_id"], "milestone_id")
            _text(milestone["title"], "milestone title", maximum=160, nullable=False)
        job = work.get("local_ai_job")
        if job is not None:
            if (not isinstance(job, dict) or set(job) != {"model_identity", "endpoint_ref",
                    "slot", "queue_status", "task_correlation_id", "started_at", "completed_at"}
                    or job.get("queue_status") not in _QUEUE_STATES):
                raise ValueError("local_ai_job record is invalid")
            for key, maximum in (("model_identity", 256), ("endpoint_ref", 512),
                                 ("slot", 128), ("task_correlation_id", 128)):
                _reference(job.get(key), key)
            _parse_time(job.get("started_at"))
            _parse_time(job.get("completed_at"))
        for key in ("created_at", "updated_at", "started_at", "completed_at"):
            _parse_time(work.get(key))
        if set(work) != {"work_order_id", "session_id", "worker_id", "owner_label", "ownership_state", "title", "detail",
                "status", "milestone", "milestones_total", "milestones", "dependencies",
                "blocker", "next_action", "evidence", "outcome", "repository", "branch",
                "pull_request", "deliverable", "local_ai_job", "created_at", "updated_at",
                "started_at", "completed_at"}:
            raise ValueError("work_order record contains unsupported fields")
        current, total = work.get("milestone"), work.get("milestones_total")
        if current is not None and (type(current) is not int or current < 0):
            raise ValueError("milestone must be a nonnegative integer or null")
        if total is not None and (type(total) is not int or total < 1):
            raise ValueError("milestones_total must be positive or null")
        if current is not None and total is not None and current > total:
            raise ValueError("milestone cannot exceed milestones_total")

    def register_worker(self, *, worker_id=None, worker_type="other", hostname=None,
                        os_name=None, capabilities=(), model_identity=None,
                        endpoint_ref=None, registered_at=None):
        worker_id = _id(worker_id or f"worker:{uuid4().hex}", "worker_id")
        worker = {"worker_id": worker_id, "worker_type": worker_type,
                  "hostname": hostname or socket.gethostname(),
                  "os": os_name or os.name, "capabilities": _string_list(capabilities, "capabilities"),
                  "model_identity": model_identity, "endpoint_ref": endpoint_ref,
                  "registered_at": _stamp(registered_at)}
        self._validate_worker(worker)
        with self._lock():
            document = self._read_unlocked()
            existing = document["workers"].get(worker_id)
            if existing:
                identity_keys = ("worker_id", "worker_type", "hostname", "os", "capabilities",
                                 "model_identity", "endpoint_ref")
                if any(existing.get(key) != worker.get(key) for key in identity_keys):
                    raise WorkRegistryError("worker_identity_conflict")
                return dict(existing)
            document["workers"][worker_id] = worker
            self._write_unlocked(document)
        return dict(worker)

    def start_session(self, worker_id, *, session_id=None, hostname=None, os_name=None,
                       repository=None, branch=None, pull_request=None,
                       model_identity=None, endpoint_ref=None, started_at=None):
        worker_id = _id(worker_id, "worker_id")
        session_id = _id(session_id or f"session:{uuid4().hex}", "session_id")
        started = _stamp(started_at)
        session = {"session_id": session_id, "worker_id": worker_id,
            "hostname": hostname, "os": os_name, "repository": repository,
            "branch": branch, "pull_request": pull_request,
            "model_identity": model_identity, "endpoint_ref": endpoint_ref,
            "lifecycle": "running", "activity_state": "unknown",
            "current_work_order_id": None, "started_at": started,
            "last_heartbeat_at": started, "last_activity_at": None, "ended_at": None}
        self._validate_session(session)
        with self._lock():
            document = self._read_unlocked()
            if worker_id not in document["workers"]:
                raise WorkRegistryError("worker_not_registered")
            if session_id in document["sessions"]:
                raise WorkRegistryError("session_id_conflict")
            document["sessions"][session_id] = session
            self._write_unlocked(document)
        return dict(session)

    def heartbeat(self, session_id, *, at=None, activity_state=None):
        session_id = _id(session_id, "session_id")
        instant = _stamp(at)
        with self._lock():
            document = self._read_unlocked()
            session = document["sessions"].get(session_id)
            if session is None:
                raise WorkRegistryError("session_not_found")
            if session["lifecycle"] != "running":
                raise WorkRegistryError("session_not_running")
            session["last_heartbeat_at"] = instant
            if activity_state is not None:
                if activity_state not in _ACTIVITY:
                    raise ValueError("activity_state is unsupported")
                session["activity_state"] = activity_state
                if activity_state != "unknown":
                    session["last_activity_at"] = instant
            self._write_unlocked(document)
            return dict(session)

    def end_session(self, session_id, *, lifecycle="completed", at=None):
        if lifecycle not in {"completed", "disconnected"}:
            raise ValueError("session end lifecycle must be completed or disconnected")
        session_id = _id(session_id, "session_id")
        instant = _stamp(at)
        with self._lock():
            document = self._read_unlocked()
            session = document["sessions"].get(session_id)
            if session is None:
                raise WorkRegistryError("session_not_found")
            if session["lifecycle"] == "running":
                session["lifecycle"] = lifecycle
                session["ended_at"] = instant
                session["activity_state"] = "unknown"
                self._write_unlocked(document)
            return dict(session)

    def acknowledge_work_order(self, work_order_id, worker_id, session_id, *, at=None):
        """Bind an existing assignment to the session that explicitly received it."""
        work_order_id = _id(work_order_id, "work_order_id")
        worker_id = _id(worker_id, "worker_id")
        session_id = _id(session_id, "session_id")
        instant = _stamp(at)
        with self._lock():
            document = self._read_unlocked()
            work = document["work_orders"].get(work_order_id)
            session = document["sessions"].get(session_id)
            if work is None:
                raise WorkRegistryError("work_order_not_found")
            if session is None or session["lifecycle"] != "running":
                raise WorkRegistryError("session_not_running")
            if session["worker_id"] != worker_id or worker_id not in document["workers"]:
                raise ValueError("assignment worker does not match registered session")
            if work["session_id"] not in {None, session_id}:
                raise WorkRegistryError("work_order_already_bound")
            if work["worker_id"] not in {None, worker_id}:
                raise WorkRegistryError("work_order_owner_conflict")
            if work["status"] in {"completed", "failed", "cancelled"}:
                raise WorkRegistryError("work_order_is_terminal")
            work.update(worker_id=worker_id, session_id=session_id,
                        ownership_state="acknowledged", status="active",
                        started_at=work["started_at"] or instant, updated_at=instant)
            session["current_work_order_id"] = work_order_id
            self._validate_work_order(work)
            self._write_unlocked(document)
            return dict(work)

    def create_work_order(self, session_id=None, *, title, work_order_id=None, status="queued",
                          worker_id=None, owner_label=None, ownership_state=None,
                          detail=None, milestone=None, milestones_total=None,
                          milestones=(), dependencies=(), blocker=None, next_action=None,
                          evidence=(), outcome=None, repository=None, branch=None,
                          pull_request=None, deliverable=None, local_ai_job=None, at=None):
        if session_id is not None:
            session_id = _id(session_id, "session_id")
        if worker_id is not None:
            worker_id = _id(worker_id, "worker_id")
        work_order_id = _id(work_order_id or f"work:{uuid4().hex}", "work_order_id")
        instant = _stamp(at)
        with self._lock():
            document = self._read_unlocked()
            session = document["sessions"].get(session_id) if session_id else None
            if session_id and session is None:
                raise WorkRegistryError("session_not_found")
            if worker_id and worker_id not in document["workers"]:
                raise WorkRegistryError("worker_not_registered")
            if session and worker_id and worker_id != session["worker_id"]:
                raise ValueError("session worker and work owner do not match")
            worker_id = session["worker_id"] if session else worker_id
            if ownership_state is None:
                ownership_state = "assigned" if worker_id else "unassigned"
            if work_order_id in document["work_orders"]:
                raise WorkRegistryError("work_order_id_conflict")
            work = {"work_order_id": work_order_id, "session_id": session_id,
                "worker_id": worker_id, "owner_label": owner_label,
                "ownership_state": ownership_state, "title": title, "detail": detail,
                "status": status, "milestone": milestone, "milestones_total": milestones_total,
                "milestones": list(milestones), "dependencies": _string_list(dependencies, "dependencies"),
                "blocker": blocker, "next_action": next_action,
                "evidence": _string_list(evidence, "evidence"), "outcome": outcome,
                "repository": repository if repository is not None else (session["repository"] if session else None),
                "branch": branch if branch is not None else (session["branch"] if session else None),
                "pull_request": pull_request if pull_request is not None else (session["pull_request"] if session else None),
                "deliverable": deliverable, "local_ai_job": local_ai_job,
                "created_at": instant, "updated_at": instant,
                "started_at": instant if status == "active" else None,
                "completed_at": instant if status in {"completed", "failed", "cancelled"} else None}
            self._validate_work_order(work)
            document["work_orders"][work_order_id] = work
            if session:
                session["current_work_order_id"] = (work_order_id if status == "active" else
                                                    session["current_work_order_id"])
            self._write_unlocked(document)
        return dict(work)

    def update_work_order(self, work_order_id, *, at=None, **changes):
        work_order_id = _id(work_order_id, "work_order_id")
        instant = _stamp(at)
        allowed = {"title", "detail", "status", "milestone", "milestones_total", "milestones",
                   "dependencies", "blocker", "next_action", "evidence", "outcome",
                   "repository", "branch", "pull_request", "deliverable", "local_ai_job",
                   "worker_id", "owner_label", "ownership_state", "session_id"}
        if set(changes) - allowed:
            raise ValueError("unsupported work-order update field")
        with self._lock():
            document = self._read_unlocked()
            work = document["work_orders"].get(work_order_id)
            if work is None:
                raise WorkRegistryError("work_order_not_found")
            old_session_id = work["session_id"]
            for key, value in changes.items():
                if key in {"dependencies", "evidence"}:
                    value = _string_list(value, key)
                elif key == "milestones":
                    value = list(value)
                work[key] = value
            work["updated_at"] = instant
            if work.get("status") == "active" and work.get("started_at") is None:
                work["started_at"] = instant
            if work.get("status") in {"completed", "failed", "cancelled"}:
                work["completed_at"] = work.get("completed_at") or instant
            self._validate_work_order(work)
            if work["worker_id"] is not None and work["worker_id"] not in document["workers"]:
                raise WorkRegistryError("worker_not_registered")
            if work["session_id"] is not None:
                target = document["sessions"].get(work["session_id"])
                if target is None:
                    raise WorkRegistryError("session_not_found")
                if target["worker_id"] != work["worker_id"]:
                    raise ValueError("session worker and work owner do not match")
            session = (document["sessions"].get(work["session_id"])
                       if work["session_id"] else None)
            if old_session_id and old_session_id != work["session_id"]:
                old_session = document["sessions"].get(old_session_id)
                if old_session and old_session["current_work_order_id"] == work_order_id:
                    old_session["current_work_order_id"] = None
            if session:
                if work["status"] == "active":
                    session["current_work_order_id"] = work_order_id
                elif session["current_work_order_id"] == work_order_id:
                    session["current_work_order_id"] = None
            self._write_unlocked(document)
            return dict(work)

    def import_document(self, source):
        """Merge a canonical v1 snapshot without deleting or rewriting source data."""
        if not isinstance(source, dict) or source.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("import must use the canonical rv.work-registry.v1 schema")
        if not all(isinstance(source.get(key), dict)
                   for key in ("workers", "sessions", "work_orders")):
            raise ValueError("import collections must be objects")
        imported = {key: dict(source[key]) for key in ("workers", "sessions", "work_orders")}
        for key, validator in (("workers", self._validate_worker),
                ("sessions", self._validate_session), ("work_orders", self._validate_work_order)):
            for record_id, record in imported[key].items():
                validator(record)
                identity_key = {"workers": "worker_id", "sessions": "session_id",
                                "work_orders": "work_order_id"}[key]
                if record_id != record[identity_key]:
                    raise ValueError("import map key does not match record identity")
        with self._lock():
            document = self._read_unlocked()
            for group in ("workers", "sessions", "work_orders"):
                for record_id, record in imported[group].items():
                    existing = document[group].get(record_id)
                    if existing is not None and existing != record:
                        raise WorkRegistryError("import_identity_conflict")
                    document[group][record_id] = record
            for session in document["sessions"].values():
                if session["worker_id"] not in document["workers"]:
                    raise ValueError("imported session references an unregistered worker")
            for work in document["work_orders"].values():
                if ((work["worker_id"] is not None and work["worker_id"] not in document["workers"])
                        or (work["session_id"] is not None and work["session_id"] not in document["sessions"])):
                    raise ValueError("imported work order references a missing identity")
                if work["session_id"] is not None and document["sessions"][work["session_id"]]["worker_id"] != work["worker_id"]:
                    raise ValueError("work order owner does not match session worker")
            self._write_unlocked(document)
        return self.snapshot()

    def snapshot(self, *, now=None):
        current = now or _now()
        if current.tzinfo is None:
            raise ValueError("snapshot time must be timezone-aware")
        with self._lock():
            document = self._read_unlocked()
        sessions = []
        for source in document["sessions"].values():
            session = dict(source)
            heartbeat = _parse_time(session["last_heartbeat_at"])
            if session["lifecycle"] != "running":
                session["status"] = session["lifecycle"]
            elif heartbeat is None or heartbeat > current:
                session["status"] = "unknown"
            elif (current - heartbeat).total_seconds() > self.stale_after_seconds:
                session["status"] = "stale"
            else:
                session["status"] = "running"
            session["heartbeat_age_seconds"] = (round(max(0.0, (current - heartbeat).total_seconds()), 1)
                                                  if heartbeat is not None else None)
            activity = _parse_time(session["last_activity_at"])
            session["activity_age_seconds"] = (round(max(0.0, (current - activity).total_seconds()), 1)
                                                 if activity is not None else None)
            sessions.append(session)
        sessions.sort(key=lambda item: item["started_at"] or "", reverse=True)
        workers = []
        for source in document["workers"].values():
            worker = dict(source)
            matching = [session for session in sessions if session["worker_id"] == worker["worker_id"]]
            statuses = {item["status"] for item in matching}
            worker["session_count"] = len(matching)
            worker["status"] = ("running" if "running" in statuses else
                "stale" if "stale" in statuses else
                "disconnected" if "disconnected" in statuses else
                "completed" if matching and statuses <= {"completed"} else "unknown")
            workers.append(worker)
        workers.sort(key=lambda item: (item["worker_type"], item["worker_id"]))
        work_orders = [dict(item) for item in document["work_orders"].values()]
        work_orders.sort(key=lambda item: item["updated_at"], reverse=True)
        return {"schema_version": SCHEMA_VERSION, "observed_at": _stamp(current),
            "stale_after_seconds": self.stale_after_seconds,
            "activity_semantics": "reported by worker; heartbeat and process liveness do not prove model reasoning",
            "workers": workers, "sessions": sessions, "work_orders": work_orders}


__all__ = ["SCHEMA_VERSION", "WorkRegistry", "WorkRegistryError"]

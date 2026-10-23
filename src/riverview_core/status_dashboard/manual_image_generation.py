# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/manual_image_generation.py
# Component: V2-MANUAL-IMAGE-GENERATION
# Revision: 1.0.4
# Purpose: Authenticated operator image generation through the registered ComfyUI worker
# Execution Model: Bounded single-worker async request with durable idempotency records
# Observability: Request ID, workflow, device identity, progress, verified artifact identity and elapsed time
# Dependencies: Existing ComfyUI worker adapter, workflow registry and Dashboard account auth
# Authority: The HTTP boundary requires an authenticated operator or Steward session
# =============================================================================
"""Durable operator-manual ComfyUI requests using Riverview's registered adapter.

This is deliberately not an Engineering assignment or an alternate image engine.
It calls the existing bounded ComfyUI action and independent verifier with a
manual provenance identity, and stores the result under an authenticated artifact
route. GPU selection remains disabled; the existing pinned ComfyUI worker is the
only execution target.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import threading
import time
from types import SimpleNamespace
from uuid import UUID

from riverview_core.worker_adapter.comfyui import (
    CAPABILITY, ComfyUIAction, ComfyUIError, ComfyUIOutputVerifier,
    ComfyUITransport, ComfyUIWorkflowRegistry,
)


class ManualImageError(RuntimeError):
    def __init__(self, code: str, status: int = 400):
        self.code = code
        self.status = status
        super().__init__(code)


class ManualImageStore:
    """Atomic, owner-only, durable JSON records; image bytes stay in artifact storage."""
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._validate_root()
        self._lock = threading.RLock()

    def _validate_root(self):
        info = self.root.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
                stat.S_IMODE(info.st_mode) != 0o700 or self.root.resolve() != self.root.absolute()):
            raise ManualImageError("manual_store_unavailable", 503)

    @staticmethod
    def _request_key(request_id: str) -> str:
        try:
            parsed = UUID(request_id)
        except (ValueError, TypeError, AttributeError):
            raise ManualImageError("manual_request_id_invalid") from None
        if str(parsed) != request_id.lower():
            raise ManualImageError("manual_request_id_invalid")
        return str(parsed)

    def path(self, request_id: str) -> Path:
        return self.root / (self._request_key(request_id) + ".json")

    def read(self, request_id: str):
        path = self.path(request_id)
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        except FileNotFoundError:
            return None
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 64 * 1024):
                raise ManualImageError("manual_record_invalid", 503)
            with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
                record = json.load(stream)
            if record.get("request_id") != self._request_key(request_id):
                raise ManualImageError("manual_record_identity_mismatch", 503)
            return record
        except (OSError, ValueError, TypeError):
            raise ManualImageError("manual_record_unavailable", 503) from None
        finally:
            os.close(fd)

    def write(self, record):
        path = self.path(record["request_id"])
        raw = json.dumps(record, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(raw) > 64 * 1024:
            raise ManualImageError("manual_record_too_large", 413)
        temp = path.with_name(path.name + ".tmp-" + os.urandom(8).hex())
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
            directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temp.unlink(missing_ok=True)

    def list(self, actor_id: str | None = None, *, limit: int = 100):
        rows = []
        with self._lock:
            for path in self.root.glob("*.json"):
                if not re.fullmatch(r"[0-9a-f-]{36}\.json", path.name):
                    continue
                record = self.read(path.stem)
                if record and (actor_id is None or record.get("actor_id") == actor_id):
                    rows.append(record)
        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        return rows[:max(1, min(100, int(limit)))]


class ManualImageGenerationService:
    """Manual mode facade over the exact registered ComfyUI action and verifier."""
    def __init__(self, *, endpoint: str, registry_path: str | Path,
                 artifact_root: str | Path, state_root: str | Path,
                 artifact_group_gid: int | None = None, timeout_seconds: int = 900,
                 poll_interval: float = 1.0, output_host: str | None = None):
        self.endpoint = endpoint
        self.registry_path = Path(registry_path)
        self.artifact_root = Path(artifact_root)
        self.state_root = Path(state_root)
        self.output_host = output_host or socket.gethostname()
        self.artifact_group_gid = artifact_group_gid
        self.registry = self._load_registry()
        self._transport = ComfyUITransport(endpoint, timeout_seconds=5.0)
        self.store = ManualImageStore(self.state_root / "requests")
        self._action = ComfyUIAction(endpoint, self.registry, self.artifact_root,
            self.state_root / "action-journals", timeout_seconds=timeout_seconds,
            poll_interval=poll_interval, progress_callback=self._progress,
            artifact_group_gid=artifact_group_gid)
        self._verifier = ComfyUIOutputVerifier(self.artifact_root,
                                                artifact_group_gid=artifact_group_gid)
        self._mutex = threading.RLock()
        self._active_request: str | None = None
        self._threads: dict[str, threading.Thread] = {}
        self._recover_interrupted()

    def _load_registry(self):
        try:
            info = self.registry_path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_size > 2 * 1024 * 1024 or
                    self.registry_path.is_symlink()):
                raise ValueError
            templates = json.loads(self.registry_path.read_text(encoding="utf-8"))
            return ComfyUIWorkflowRegistry(templates)
        except (OSError, ValueError, TypeError):
            raise ManualImageError("workflow_registry_unavailable", 503) from None

    def _template(self, workflow_id: str):
        # Public access is derived from the runtime registry, never an allowlist in
        # the website or request handler.
        template = self.registry._templates.get(workflow_id)
        if template is None:
            raise ManualImageError("workflow_not_registered", 400)
        return copy.deepcopy(template)

    def catalog(self):
        workflows = []
        for workflow_id, template in sorted(self.registry._templates.items()):
            fixed = {}
            for node_id, node in template["workflow"].items():
                if node.get("class_type") in {"EmptyLatentImage", "EmptyImage"}:
                    inputs = node.get("inputs", {})
                    if type(inputs.get("width")) is int and type(inputs.get("height")) is int:
                        fixed["width"] = inputs["width"]
                        fixed["height"] = inputs["height"]
            parameters = []
            for name, binding in template["bindings"].items():
                item = {"name": name, **copy.deepcopy(binding)}
                node_inputs = template["workflow"][binding["node"]].get("inputs", {})
                if binding["type"] != "text" and binding["input"] in node_inputs:
                    item["default"] = copy.deepcopy(node_inputs[binding["input"]])
                parameters.append(item)
            workflows.append({"workflow_id": workflow_id,
                "revision": template["revision"], "parameters": parameters,
                "fixed_resolution": fixed or None,
                "output_nodes": list(template["output_nodes"])})
        return {"schema_version": "rv.manual-image.catalog.v1", "workflows": workflows,
            "gpu_selection_supported": False,
            "gpu_selection_reason": "The configured ComfyUI worker is pinned to its approved device. Per-request GPU allocation is not implemented; telemetry availability is not proof of a free GPU.",
            "worker": self.worker_status()}

    def worker_status(self):
        result = {"status": "unknown", "device": None,
                  "selection_mode": "fixed_configured_worker"}
        try:
            _, raw, _ = self._transport.request("GET", "/system_stats", max_bytes=256 * 1024)
            payload = json.loads(raw)
            devices = payload.get("devices")
            # ComfyUI reports the worker's executing device only when it has one
            # visible adapter. Never guess that devices[0] is the GPU assigned to
            # this worker when multiple devices are exposed.
            if not isinstance(devices, list) or len(devices) != 1:
                return result
            device = devices[0]
            if not isinstance(device, dict):
                return result
            name = device.get("name")
            if not isinstance(name, str) or len(name) > 160:
                return result
            result.update(status="ready", device={
                "name": name, "gpu_uuid": device.get("gpu_uuid")
                    if isinstance(device.get("gpu_uuid"), str) else None,
                "identity_state": "verified" if isinstance(device.get("gpu_uuid"), str)
                    else "unavailable",
                "memory_total_bytes": _optional_int(device.get("vram_total")),
                "memory_free_bytes": _optional_int(device.get("vram_free"))})
        except (ComfyUIError, OSError, ValueError, TypeError):
            pass
        return result

    def submit(self, *, request_id: str, actor_id: str, actor_role: str,
               workflow_id: str, parameters: dict):
        request_id = ManualImageStore._request_key(request_id)
        if not isinstance(actor_id, str) or not actor_id or len(actor_id) > 256:
            raise ManualImageError("manual_actor_invalid", 403)
        if actor_role not in {"operator", "steward"}:
            raise ManualImageError("manual_generation_not_authorized", 403)
        if not isinstance(parameters, dict):
            raise ManualImageError("workflow_parameters_invalid", 400)
        # Validate against the exact approved graph before persisting or calling
        # ComfyUI. This also rejects unrequested GPU overrides.
        try:
            self.registry.render(workflow_id, parameters)
        except (ValueError, TypeError):
            raise ManualImageError("workflow_parameters_invalid", 400) from None
        fingerprint = hashlib.sha256(json.dumps({"workflow_id": workflow_id,
            "parameters": parameters}, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        with self._mutex, self.store._lock:
            previous = self.store.read(request_id)
            if previous:
                if (previous.get("actor_id") != actor_id or
                        previous.get("request_sha256") != fingerprint):
                    raise ManualImageError("manual_request_id_conflict", 409)
                return self._public(previous)
            worker = self.worker_status()
            if worker.get("status") != "ready":
                raise ManualImageError("comfyui_worker_unavailable", 503)
            if self._active_request is not None:
                active = self.store.read(self._active_request)
                if active and active.get("status") in {"queued", "running", "collecting"}:
                    raise ManualImageError("comfyui_worker_busy", 409)
                self._active_request = None
            now = _utc_now()
            record = {"schema_version": "rv.manual-image.request.v1",
                "request_id": request_id, "execution_kind": "operator_manual",
                "actor_id": actor_id, "actor_role": actor_role,
                "workflow_id": workflow_id, "workflow_revision": self._template(workflow_id)["revision"],
                "parameters": copy.deepcopy(parameters), "request_sha256": fingerprint,
                "worker": copy.deepcopy(worker),
                "status": "queued", "created_at": now, "updated_at": now,
                "started_at": None, "completed_at": None, "elapsed_seconds": None,
                "progress": {"status": "queued", "outputs_saved": 0},
                "verification": None, "artifact": None, "error_code": None,
                "comfy_prompt_id": None, "work_order_id": None,
                "engineering_assignment_id": None}
            self.store.write(record)
            self._active_request = request_id
            thread = threading.Thread(target=self._run, args=(request_id,),
                name="manual-image-" + request_id[:8], daemon=True)
            self._threads[request_id] = thread
            thread.start()
            return self._public(record)

    def _recover_interrupted(self):
        for record in self.store.list(limit=100):
            if record.get("status") not in {"queued", "running", "collecting"}:
                continue
            request_id = record["request_id"]
            if self._active_request is not None:
                break
            self._active_request = request_id
            thread = threading.Thread(target=self._run, args=(request_id,),
                name="manual-image-recovery-" + request_id[:8], daemon=True)
            self._threads[request_id] = thread
            thread.start()

    def _progress(self, update):
        if not isinstance(update, dict) or not isinstance(update.get("assignment_id"), str):
            return
        request_id = update["assignment_id"].removeprefix("manual:")
        with self.store._lock:
            record = self.store.read(request_id)
            if not record or record.get("status") not in {"queued", "running", "collecting"}:
                return
            record["status"] = "collecting" if update.get("outputs_saved", 0) else "running"
            record["comfy_prompt_id"] = update.get("prompt_id")
            record["progress"] = {"status": str(update.get("status", "running"))[:32],
                                  "outputs_saved": _optional_int(update.get("outputs_saved")) or 0}
            record["updated_at"] = _utc_now()
            self.store.write(record)

    def _run(self, request_id: str):
        record = self.store.read(request_id)
        if not record:
            return
        start = time.monotonic()
        started_at = record.get("started_at") or _utc_now()
        record.update(status="running", started_at=started_at, updated_at=started_at,
                      error_code=None)
        self.store.write(record)
        manual_identity = "manual:" + request_id
        try:
            result = self._action({"id": manual_identity}, SimpleNamespace(value={
                "workflow_id": record["workflow_id"], "parameters": record["parameters"]}))
            attempt = {"attempt_id": request_id, "status": "succeeded",
                "capability": CAPABILITY,
                "result_sha256": hashlib.sha256(json.dumps(dict(result), sort_keys=True,
                    separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()}
            decision = self._verifier.verify({"id": manual_identity}, attempt, result)
            if getattr(decision.status, "value", decision.status) != "ACCEPTED":
                raise ManualImageError("independent_verification_rejected", 502)
            artifact = result["artifacts"][0]
            if artifact.get("media_type") != "image/png":
                raise ManualImageError("workflow_output_not_png", 502)
            path = Path(result["artifact_path"])
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_size != artifact["bytes"]:
                raise ManualImageError("verified_artifact_path_invalid", 502)
            with path.open("rb") as stream:
                header = stream.read(24)
            if (len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or
                    header[12:16] != b"IHDR"):
                raise ManualImageError("verified_png_header_invalid", 502)
            width, height = struct.unpack(">II", header[16:24])
            if not 1 <= width <= 8192 or not 1 <= height <= 8192:
                raise ManualImageError("verified_png_dimensions_invalid", 502)
            record = self.store.read(request_id)
            record.update(status="complete", updated_at=_utc_now(), completed_at=_utc_now(),
                elapsed_seconds=round(time.monotonic() - start, 3),
                comfy_prompt_id=result.get("prompt_id"),
                progress={"status": "complete", "outputs_saved": len(result["artifacts"])},
                verification={"decision": "ACCEPTED", "verifier": "ComfyUIOutputVerifier",
                    "verifier_revision": decision.verifier_revision,
                    "criteria": dict(decision.criteria)},
                artifact={"storage_name": artifact["storage_name"],
                    "absolute_path": str(path.resolve()), "host": self.output_host,
                    "media_type": artifact["media_type"], "size_bytes": artifact["bytes"],
                    "sha256": artifact["sha256"], "width": width, "height": height,
                    "device": copy.deepcopy(record.get("worker", {}).get("device")),
                    "download_url": f"/api/v1/manual-image-generations/{request_id}/image"},
                error_code=None)
            self.store.write(record)
        except ManualImageError as exc:
            self._fail(request_id, exc.code, start)
        except ComfyUIError as exc:
            self._fail(request_id, exc.code, start)
        except Exception:
            self._fail(request_id, "manual_generation_failed", start)
        finally:
            with self._mutex:
                if self._active_request == request_id:
                    self._active_request = None

    def _fail(self, request_id: str, code: str, started):
        with self.store._lock:
            record = self.store.read(request_id)
            if not record:
                return
            record.update(status="failed", updated_at=_utc_now(), completed_at=_utc_now(),
                elapsed_seconds=round(time.monotonic() - started, 3),
                error_code=code[:80], progress={"status": "failed", "outputs_saved": 0})
            self.store.write(record)

    @staticmethod
    def _public(record):
        return copy.deepcopy(record)

    def get(self, request_id: str):
        record = self.store.read(request_id)
        return self._public(record) if record else None

    def history(self, actor_id: str | None = None, *, limit: int = 100):
        return [self._public(record) for record in self.store.list(actor_id, limit=limit)]

    def image_bytes(self, request_id: str):
        record = self.store.read(request_id)
        if not record or record.get("status") != "complete" or not record.get("artifact"):
            return None
        artifact = record["artifact"]
        relative = artifact.get("storage_name", "").split("/")
        if (len(relative) != 2 or not re.fullmatch(r"[0-9a-f]{64}", relative[0]) or
                not re.fullmatch(r"[0-9a-f]{12}", relative[1])
                or artifact.get("media_type") != "image/png"):
            raise ManualImageError("manual_artifact_reference_invalid", 503)
        root_fd = os.open(self.artifact_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            root_info = os.fstat(root_fd)
            expected_root_mode = 0o2750 if self.artifact_group_gid is not None else 0o700
            if (not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != os.geteuid() or
                    stat.S_IMODE(root_info.st_mode) != expected_root_mode or
                    (self.artifact_group_gid is not None and
                     root_info.st_gid != self.artifact_group_gid)):
                raise ManualImageError("manual_artifact_integrity_failed", 503)
            parent_fd = os.open(relative[0], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=root_fd)
            try:
                parent_info = os.fstat(parent_fd)
                expected_parent_mode = 0o2750 if self.artifact_group_gid is not None else 0o700
                if (not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != os.geteuid() or
                        stat.S_IMODE(parent_info.st_mode) != expected_parent_mode or
                        (self.artifact_group_gid is not None and
                         parent_info.st_gid != self.artifact_group_gid)):
                    raise ManualImageError("manual_artifact_integrity_failed", 503)
                fd = os.open(relative[1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
                try:
                    info = os.fstat(fd)
                    expected_mode = 0o640 if self.artifact_group_gid is not None else 0o600
                    if (not stat.S_ISREG(info.st_mode) or info.st_uid != root_info.st_uid
                            or info.st_size != artifact.get("size_bytes")
                            or info.st_size > 16 * 1024 * 1024
                            or stat.S_IMODE(info.st_mode) != expected_mode
                            or (self.artifact_group_gid is not None and
                                info.st_gid != self.artifact_group_gid)):
                        raise ManualImageError("manual_artifact_integrity_failed", 503)
                    chunks = []
                    total = 0
                    while total <= 16 * 1024 * 1024:
                        chunk = os.read(fd, min(65536, 16 * 1024 * 1024 + 1 - total))
                        if not chunk:
                            break
                        chunks.append(chunk); total += len(chunk)
                    data = b"".join(chunks)
                finally:
                    os.close(fd)
            finally:
                os.close(parent_fd)
        finally:
            os.close(root_fd)
        if (len(data) != artifact["size_bytes"] or
                hashlib.sha256(data).hexdigest() != artifact["sha256"] or
                ComfyUIAction._image_type(data) != "image/png"):
            raise ManualImageError("manual_artifact_integrity_failed", 503)
        return record, data


def _optional_int(value):
    return value if type(value) is int and value >= 0 else None


def _utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

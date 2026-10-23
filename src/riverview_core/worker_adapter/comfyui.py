# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/comfyui.py
# Component: ENGINEERING-COMFYUI-ADAPTER
# Revision: 1.0.6
# Changed: 2026-10-23 UTC | RV-ISSUE-252 | Safely finalize shared assignment directories and artifact files despite the service's private umask.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Accept canonical colon-delimited Riverview assignment IDs in durable artifact storage.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Restrict dashboard artifact sharing to group read and traversal.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Keep execution journals private while sharing accepted image artifacts with the dashboard group.
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Support an explicitly shared read-only artifact group for the authenticated dashboard download path.
# Purpose: Execute immutable registered ComfyUI workflows as bounded Engineering work
# Execution Model: Durable local journal, bounded HTTP polling, assignment-bound image files
# Observability: Prompt, workflow, progress, artifact size and SHA-256; no image body logs
# Dependencies: Python 3.10+; standard library; configured ComfyUI HTTP endpoint
# Authority: Worker registration and exact assignment.execute grant remain mandatory
# Tests: tests/test_comfyui_adapter.py
# =============================================================================
"""Bounded ComfyUI worker action and independent output-integrity verifier.

A template registry is provisioned by the operator; assignments may choose only a
registered template and validated parameters. Ambiguous prompt submissions are
journaled as indeterminate and are never blindly replayed.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import threading
import time
import zlib
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .knowledge import KnowledgeResult, KnowledgeStatus
from .verifier import VerificationResult, VerificationStatus

CAPABILITY = "engineering.comfyui-image.v1"
SCHEMA = "rv.engineering.comfyui-artifacts.v1"
MAX_TEMPLATE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 48 * 1024 * 1024
MAX_OUTPUTS = 8
MAX_STATUS_BYTES = 2 * 1024 * 1024


class ComfyUIError(RuntimeError):
    """Sanitized ComfyUI action failure."""
    def __init__(self, code: str, *, execution_started: bool | None = None):
        self.code = code
        self.execution_started = execution_started
        super().__init__(code)


class ComfyUITemplateError(ValueError):
    """Invalid or unregistered workflow template or parameter set."""


class ComfyUITransport:
    """Small bounded HTTP client; endpoint is fixed at trusted service startup."""
    def __init__(self, endpoint: str, *, timeout_seconds: float = 5.0):
        parsed = urlsplit(endpoint)
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
        except ValueError:
            address = None
        if (parsed.scheme != "http" or address is None or
                not (address.is_loopback or address.is_private) or parsed.username or
                parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError("ComfyUI endpoint must be a plain configured HTTP origin")
        if not 0.1 <= timeout_seconds <= 30:
            raise ValueError("ComfyUI request timeout must be from 0.1 to 30 seconds")
        self.base = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(self, method: str, path: str, *, payload=None, max_bytes=MAX_STATUS_BYTES):
        if not path.startswith("/") or ".." in path.split("/"):
            raise ComfyUIError("request_path_invalid")
        raw = None if payload is None else json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        headers = {"Accept": "application/json, image/*, application/octet-stream"}
        if raw is not None:
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=raw, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ComfyUIError("response_size_exceeded")
                return response.status, data, response.headers.get_content_type()
        except HTTPError as exc:
            raise ComfyUIError(f"http_{exc.code}", execution_started=(method != "POST")) from None
        except (URLError, TimeoutError, OSError):
            raise ComfyUIError("connection_lost", execution_started=(method == "POST")) from None


class ComfyUIWorkflowRegistry:
    """In-memory immutable registry of operator-reviewed workflow graphs."""
    def __init__(self, templates: dict[str, dict]):
        if not isinstance(templates, dict) or not templates or len(templates) > 32:
            raise ValueError("one to 32 registered workflows are required")
        self._templates = {}
        for name, item in templates.items():
            if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", name):
                raise ValueError("workflow id is invalid")
            self._templates[name] = self._validate_template(item)

    @staticmethod
    def _validate_template(item):
        if not isinstance(item, dict) or set(item) != {"revision", "workflow", "bindings", "output_nodes"}:
            raise ValueError("workflow template fields are invalid")
        graph = item["workflow"]
        if not isinstance(graph, dict) or not graph:
            raise ValueError("workflow graph is invalid")
        raw = json.dumps(graph, separators=(",", ":"), allow_nan=False).encode()
        if len(raw) > MAX_TEMPLATE_BYTES:
            raise ValueError("workflow graph exceeds limit")
        for node, detail in graph.items():
            if (not isinstance(node, str) or not re.fullmatch(r"[0-9]{1,12}", node) or
                    not isinstance(detail, dict) or not isinstance(detail.get("class_type"), str) or
                    not isinstance(detail.get("inputs"), dict)):
                raise ValueError("workflow graph node is invalid")
        bindings = item["bindings"]
        outputs = item["output_nodes"]
        if not isinstance(item["revision"], str) or not 1 <= len(item["revision"]) <= 80:
            raise ValueError("workflow revision is invalid")
        if not isinstance(bindings, dict) or len(bindings) > 32:
            raise ValueError("workflow bindings are invalid")
        for key, binding in bindings.items():
            if (not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", key) or
                    not isinstance(binding, dict) or set(binding) -
                    {"node", "input", "type", "min", "max", "max_length", "choices"} or
                    binding.get("node") not in graph or
                    binding.get("input") not in graph[binding["node"]]["inputs"] or
                    binding.get("type") not in {"integer", "number", "text", "choice"}):
                raise ValueError("workflow parameter binding is invalid")
            if binding["type"] == "choice" and (
                    not isinstance(binding.get("choices"), list) or
                    not 1 <= len(binding["choices"]) <= 64 or
                    any(not isinstance(choice, str) or not choice or len(choice) > 128
                        for choice in binding["choices"]) or
                    len(set(binding["choices"])) != len(binding["choices"])):
                raise ValueError("workflow choices are invalid")
            if binding["type"] in {"integer", "number"}:
                for bound in ("min", "max"):
                    if bound in binding and (type(binding[bound]) not in (int, float) or
                            abs(binding[bound]) > 1e9):
                        raise ValueError("workflow numeric bound is invalid")
                if ("min" in binding and "max" in binding and
                        binding["min"] > binding["max"]):
                    raise ValueError("workflow numeric range is invalid")
            if binding["type"] == "text" and (
                    type(binding.get("max_length", 256)) is not int or
                    not 1 <= binding.get("max_length", 256) <= 4096):
                raise ValueError("workflow text bound is invalid")
        if (not isinstance(outputs, list) or not 1 <= len(outputs) <= MAX_OUTPUTS or
                any(node not in graph for node in outputs) or len(set(outputs)) != len(outputs)):
            raise ValueError("workflow output nodes are invalid")
        return copy.deepcopy(item)

    def render(self, workflow_id: str, parameters: dict):
        if workflow_id not in self._templates:
            raise ComfyUITemplateError("workflow_not_registered")
        template = self._templates[workflow_id]
        if not isinstance(parameters, dict) or set(parameters) != set(template["bindings"]):
            raise ComfyUITemplateError("workflow_parameters_invalid")
        graph = copy.deepcopy(template["workflow"])
        for name, value in parameters.items():
            binding = template["bindings"][name]
            kind = binding["type"]
            if kind == "integer":
                valid = type(value) is int
            elif kind == "number":
                valid = type(value) in (int, float) and value == value and abs(value) != float("inf")
            elif kind == "text":
                valid = isinstance(value, str) and len(value.encode("utf-8")) <= binding.get("max_length", 256)
            else:
                valid = isinstance(value, str) and value in binding.get("choices", [])
            if not valid:
                raise ComfyUITemplateError("workflow_parameter_type_invalid")
            if kind in {"integer", "number"}:
                if "min" in binding and value < binding["min"] or "max" in binding and value > binding["max"]:
                    raise ComfyUITemplateError("workflow_parameter_out_of_range")
            graph[binding["node"]]["inputs"][binding["input"]] = value
        template_digest = hashlib.sha256(json.dumps(
            template, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return graph, template, template_digest


class ComfyUIKnowledgeProvider:
    """Bind verified existing worker-contract grounding to a work-order resolver.

    ``request_resolver`` must read only the already-authorized persisted Engineering
    request and return ``{"workflow_id": ..., "parameters": ...}``. Its output is
    checked again by ``ComfyUIWorkflowRegistry`` before any network effect.
    """
    def __init__(self, provider, request_resolver):
        if not callable(request_resolver):
            raise ValueError("a persisted-work-order request resolver is required")
        self.provider = provider
        self.request_resolver = request_resolver

    def _bind(self, assignment, result):
        if result.status is not KnowledgeStatus.VERIFIED:
            return result
        try:
            request = self.request_resolver(assignment)
        except Exception:
            return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)
        if (not isinstance(request, dict) or set(request) != {"workflow_id", "parameters"} or
                not isinstance(request.get("workflow_id"), str) or
                not isinstance(request.get("parameters"), dict)):
            return KnowledgeResult(KnowledgeStatus.UNVERIFIED,
                source_references=result.source_references,
                source_revision=result.source_revision, source_sha256=result.source_sha256,
                retrieval_complete=False)
        return KnowledgeResult(result.status, value=request,
            source_references=result.source_references,
            source_revision=result.source_revision, source_sha256=result.source_sha256,
            retrieval_complete=result.retrieval_complete)

    def ground_assignment(self, assignment):
        return self._bind(assignment, self.provider.ground_assignment(assignment))

    def preflight_action(self, assignment, action):
        return self.provider.preflight_action(assignment, action)

    def reground_assignment(self, assignment, trigger):
        result = self.provider.reground_assignment(assignment, trigger)
        return self._bind(assignment, result)

    def record_learning(self, assignment, outcome):
        return self.provider.record_learning(assignment, outcome)


class ComfyUIAction:
    """Submit registered workflows and save bounded outputs with crash recovery."""
    CAPABILITY = CAPABILITY
    timeout_seconds = 900

    def __init__(self, endpoint: str, registry: ComfyUIWorkflowRegistry,
                 artifact_root: str | Path, state_root: str | Path, *,
                 timeout_seconds: float = 900, poll_interval: float = 1.0,
                 request_timeout_seconds: float = 5.0, progress_callback=None,
                 artifact_group_gid: int | None = None):
        if not 5 <= timeout_seconds <= 3600 or not 0.1 <= poll_interval <= 10:
            raise ValueError("execution bounds are invalid")
        self.transport = ComfyUITransport(endpoint, timeout_seconds=request_timeout_seconds)
        self.registry = registry
        self.artifact_root = Path(artifact_root)
        self.state_root = Path(state_root)
        self.timeout_seconds = timeout_seconds
        self.poll_interval = poll_interval
        if progress_callback is not None and not callable(progress_callback):
            raise ValueError("progress_callback must be callable")
        self.progress_callback = progress_callback
        if artifact_group_gid is not None and (type(artifact_group_gid) is not int or artifact_group_gid <= 0):
            raise ValueError("artifact group ID must be a positive integer")
        self.artifact_group_gid = artifact_group_gid
        self._lock = threading.RLock()

    def _prepare_root(self, root, *, shared=False):
        group_gid = self.artifact_group_gid if shared else None
        root.mkdir(mode=0o2750 if group_gid is not None else 0o700,
                   parents=True, exist_ok=True)
        info = root.lstat()
        expected_mode = 0o2750 if group_gid is not None else 0o700
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
                stat.S_IMODE(info.st_mode) != expected_mode or
                (group_gid is not None and info.st_gid != group_gid) or
                root.resolve() != root.absolute()):
            raise ComfyUIError("artifact_directory_unsafe")

    def __call__(self, assignment, grounded):
        value = grounded.value
        if not isinstance(value, dict) or set(value) != {"workflow_id", "parameters"}:
            raise ComfyUITemplateError("grounded_workflow_request_invalid")
        graph, template, template_digest = self.registry.render(value["workflow_id"], value["parameters"])
        assignment_id = str(assignment.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9:._-]{1,128}", assignment_id):
            raise ComfyUITemplateError("assignment_id_invalid")
        self._prepare_root(self.artifact_root, shared=True)
        self._prepare_root(self.state_root)
        key = hashlib.sha256(assignment_id.encode()).hexdigest()
        journal = self.state_root / (key + ".json")
        cancel_marker = self.state_root / (key + ".cancel")
        lock_path = self.state_root / (key + ".lock")
        with self._lock, lock_path.open("a+b") as lockfile:
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
            if cancel_marker.exists():
                raise ComfyUIError("execution_cancelled", execution_started=True)
            state = self._read_journal(journal, assignment_id)
            if state:
                if state.get("template_sha256") != template_digest:
                    raise ComfyUIError("workflow_changed_after_submission", execution_started=True)
                if state.get("status") == "complete":
                    return state["result"]
                if state.get("status") in {"submitting", "indeterminate"}:
                    if state.get("status") == "submitting":
                        state["status"] = "indeterminate"
                        self._write_journal(journal, state)
                    raise ComfyUIError("submission_outcome_indeterminate", execution_started=True)
                if state.get("status") in {"cancelled", "failed"}:
                    raise ComfyUIError("execution_" + state["status"], execution_started=True)
                if not isinstance(state.get("prompt_id"), str):
                    raise ComfyUIError("execution_journal_prompt_id_missing", execution_started=True)
            else:
                state = {"schema": "rv.comfyui.execution.v1", "assignment_id": assignment_id,
                         "workflow_id": value["workflow_id"], "workflow_revision": template["revision"],
                         "template_sha256": template_digest,
                         "request_sha256": hashlib.sha256(json.dumps(graph, sort_keys=True,
                            separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
                         "status": "submitting", "prompt_id": None, "outputs": []}
                self._write_journal(journal, state)
                try:
                    status, raw, _ = self.transport.request("POST", "/prompt", payload={
                        "prompt": graph, "client_id": "riverview-" + key,
                        "extra_data": {"riverview_assignment": assignment_id,
                                       "riverview_template_sha256": template_digest}},
                        max_bytes=64 * 1024)
                    response = json.loads(raw)
                    prompt_id = response.get("prompt_id")
                    if status != 200 or not isinstance(prompt_id, str) or not re.fullmatch(
                            r"[A-Fa-f0-9-]{8,80}", prompt_id):
                        raise ComfyUIError("prompt_response_invalid", execution_started=True)
                    state.update(status="submitted", prompt_id=prompt_id)
                    self._write_journal(journal, state)
                except ComfyUIError as exc:
                    if exc.execution_started is not False:
                        state["status"] = "indeterminate"
                        self._write_journal(journal, state)
                    raise
                except (ValueError, TypeError, KeyError):
                    state["status"] = "indeterminate"
                    self._write_journal(journal, state)
                    raise ComfyUIError("prompt_response_invalid", execution_started=True) from None
            return self._collect_until_complete(assignment_id, template, template_digest,
                                                journal, state, cancel_marker)

    def _collect_until_complete(self, assignment_id, template, template_digest, journal, state,
                                cancel_marker):
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            if cancel_marker.exists():
                state["status"] = "cancelled"
                self._write_journal(journal, state)
                raise ComfyUIError("execution_cancelled", execution_started=True)
            self._report_progress(assignment_id, state, "running")
            status, raw, _ = self.transport.request(
                "GET", "/history/" + state["prompt_id"], max_bytes=MAX_STATUS_BYTES)
            if status != 200:
                raise ComfyUIError("history_status_invalid", execution_started=True)
            try:
                history = json.loads(raw)
            except ValueError:
                raise ComfyUIError("history_schema_invalid", execution_started=True) from None
            record = history.get(state["prompt_id"])
            if record and isinstance(record, dict):
                status_info = record.get("status", {})
                prompt_record = record.get("prompt")
                # ComfyUI history encodes [queue_number, prompt_id, workflow,
                # extra_data, outputs_to_execute]. Identity is carried in the
                # extra_data slot (index 3), never in the workflow graph (index 2).
                if (not isinstance(prompt_record, list) or len(prompt_record) < 4 or
                        prompt_record[1] != state["prompt_id"] or
                        not isinstance(prompt_record[2], dict) or
                        not isinstance(prompt_record[3], dict) or
                        prompt_record[3].get("riverview_assignment") != assignment_id or
                        prompt_record[3].get("riverview_template_sha256") != template_digest):
                    raise ComfyUIError("history_identity_mismatch", execution_started=True)
                if isinstance(status_info, dict) and status_info.get("status_str") == "error":
                    state["status"] = "failed"
                    self._write_journal(journal, state)
                    raise ComfyUIError("workflow_execution_failed", execution_started=True)
                outputs = record.get("outputs", {})
                if not isinstance(outputs, dict):
                    raise ComfyUIError("history_schema_invalid", execution_started=True)
                refs = []
                for node in template["output_nodes"]:
                    node_output = outputs.get(str(node), {})
                    images = node_output.get("images", []) if isinstance(node_output, dict) else []
                    if not isinstance(images, list):
                        raise ComfyUIError("output_schema_invalid", execution_started=True)
                    refs.extend(images)
                if refs:
                    if len(refs) > MAX_OUTPUTS:
                        raise ComfyUIError("output_count_exceeded", execution_started=True)
                    state["status"] = "collecting"
                    for idx, ref in enumerate(refs):
                        if idx < len(state["outputs"]):
                            continue
                        output = self._retrieve_image(assignment_id, idx, ref, state["outputs"])
                        state["outputs"].append(output)
                        self._write_journal(journal, state)
                    if cancel_marker.exists():
                        state["status"] = "cancelled"
                        self._write_journal(journal, state)
                        raise ComfyUIError("execution_cancelled", execution_started=True)
                    result = self._result(assignment_id, state)
                    state.update(status="complete", result=result)
                    self._write_journal(journal, state)
                    self._report_progress(assignment_id, state, "complete")
                    return result
            time.sleep(self.poll_interval)
        state["status"] = "timed_out"
        self._write_journal(journal, state)
        raise ComfyUIError("execution_timeout", execution_started=True)

    def _report_progress(self, assignment_id, state, default_status):
        """Publish bounded queue state without including prompts or image data."""
        if self.progress_callback is None:
            return
        try:
            _, raw, _ = self.transport.request("GET", "/queue", max_bytes=128 * 1024)
            queue = json.loads(raw)
            prompt_id = state.get("prompt_id")
            running = any(isinstance(row, list) and len(row) > 1 and row[1] == prompt_id
                          for row in queue.get("queue_running", []))
            pending = any(isinstance(row, list) and len(row) > 1 and row[1] == prompt_id
                          for row in queue.get("queue_pending", []))
            current = "running" if running else "queued" if pending else default_status
        except (ComfyUIError, ValueError, TypeError, AttributeError):
            current = default_status
        try:
            self.progress_callback({"assignment_id": assignment_id,
                "prompt_id": state.get("prompt_id"), "status": current,
                "outputs_saved": len(state.get("outputs", []))})
        except Exception:
            pass

    def _retrieve_image(self, assignment_id, index, ref, existing_outputs):
        if not isinstance(ref, dict) or set(ref) - {"filename", "subfolder", "type"}:
            raise ComfyUIError("image_reference_invalid", execution_started=True)
        filename, subfolder, kind = ref.get("filename"), ref.get("subfolder", ""), ref.get("type", "output")
        if (not isinstance(filename, str) or not filename or len(filename) > 240 or
                Path(filename).name != filename or filename in {".", ".."} or
                "/" in filename or "\\" in filename or "\\" in subfolder or
                not isinstance(subfolder, str) or len(subfolder) > 240 or
                PurePosixPath(subfolder).is_absolute() or ".." in PurePosixPath(subfolder).parts or
                kind not in {"output", "temp"}):
            raise ComfyUIError("image_reference_invalid", execution_started=True)
        query = urlencode({"filename": filename, "subfolder": subfolder, "type": kind})
        _, raw, _ = self.transport.request("GET", "/view?" + query, max_bytes=MAX_IMAGE_BYTES)
        if not raw or not self._image_type(raw):
            raise ComfyUIError("image_content_invalid", execution_started=True)
        current = sum(item["bytes"] for item in existing_outputs)
        if current + len(raw) > MAX_TOTAL_IMAGE_BYTES:
            raise ComfyUIError("image_total_size_exceeded", execution_started=True)
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[self._image_type(raw)]
        assignment_key = hashlib.sha256(assignment_id.encode()).hexdigest()
        output_name = f"comfyui-output-{index + 1}.{ext}"
        storage_key = hashlib.sha256(output_name.encode()).hexdigest()[:12]
        assignment_dir = self.artifact_root / assignment_key
        assignment_mode = 0o2750 if self.artifact_group_gid is not None else 0o700
        self._prepare_assignment_directory(assignment_dir, assignment_mode)
        destination = assignment_dir / storage_key
        self._atomic_bytes(destination, raw,
                           mode=0o640 if self.artifact_group_gid is not None else 0o600)
        return {"name": output_name, "storage_name": f"{assignment_key}/{storage_key}",
                "media_type": self._image_type(raw), "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}

    def _prepare_assignment_directory(self, directory, expected_mode):
        """Create an assignment directory and apply its exact safe mode.

        systemd's UMask=0077 masks group read/traverse bits requested by mkdir,
        even beneath the already validated setgid artifact root. Repair only the
        resulting restrictive 02700 mode, and only after validating the owned
        directory through an O_NOFOLLOW descriptor. All other mismatches fail
        closed.
        """
        try:
            directory.mkdir(mode=expected_mode, exist_ok=False)
        except FileExistsError:
            pass
        except OSError:
            raise ComfyUIError("artifact_assignment_directory_unsafe", execution_started=True) from None

        try:
            path_info = directory.lstat()
            if (not stat.S_ISDIR(path_info.st_mode) or path_info.st_uid != os.geteuid() or
                    (self.artifact_group_gid is not None and
                     path_info.st_gid != self.artifact_group_gid)):
                raise ComfyUIError("artifact_assignment_directory_unsafe", execution_started=True)
            mode = stat.S_IMODE(path_info.st_mode)
            if mode == expected_mode:
                return
            if expected_mode != 0o2750 or mode != 0o2700:
                raise ComfyUIError("artifact_assignment_directory_unsafe", execution_started=True)

            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(directory, flags)
            try:
                opened_info = os.fstat(fd)
                if (not stat.S_ISDIR(opened_info.st_mode) or
                        (opened_info.st_dev, opened_info.st_ino) !=
                        (path_info.st_dev, path_info.st_ino) or
                        opened_info.st_uid != os.geteuid() or
                        opened_info.st_gid != self.artifact_group_gid or
                        stat.S_IMODE(opened_info.st_mode) != 0o2700):
                    raise ComfyUIError("artifact_assignment_directory_unsafe", execution_started=True)
                os.fchmod(fd, expected_mode)
            finally:
                os.close(fd)
        except ComfyUIError:
            raise
        except OSError:
            raise ComfyUIError("artifact_assignment_directory_unsafe", execution_started=True) from None

    @staticmethod
    def _image_type(raw):
        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
            position = 8
            saw_header = saw_data = saw_end = False
            while position + 12 <= len(raw):
                size = int.from_bytes(raw[position:position + 4], "big")
                end = position + 12 + size
                if end > len(raw):
                    return None
                kind = raw[position + 4:position + 8]
                data = raw[position + 8:position + 8 + size]
                crc = int.from_bytes(raw[position + 8 + size:end], "big")
                if zlib.crc32(kind + data) & 0xffffffff != crc:
                    return None
                if kind == b"IHDR" and size == 13 and position == 8:
                    saw_header = True
                elif kind == b"IDAT":
                    saw_data = True
                elif kind == b"IEND" and size == 0 and end == len(raw):
                    saw_end = True
                    break
                position = end
            if saw_header and saw_data and saw_end:
                return "image/png"
            return None
        if len(raw) >= 4 and raw.startswith(b"\xff\xd8\xff") and raw.endswith(b"\xff\xd9"):
            return "image/jpeg"
        if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            if int.from_bytes(raw[4:8], "little") + 8 == len(raw):
                return "image/webp"
        return None

    def _result(self, assignment_id, state):
        first = state["outputs"][0]
        return {"artifact_schema": SCHEMA, "assignment_id": assignment_id,
                "workflow_id": state["workflow_id"], "workflow_revision": state["workflow_revision"],
                "template_sha256": state["template_sha256"], "prompt_id": state["prompt_id"],
                "artifact_name": first["storage_name"],
                "artifact_path": str(self.artifact_root / first["storage_name"]),
                "artifact_sha256": first["sha256"], "artifact_bytes": first["bytes"],
                "artifacts": copy.deepcopy(state["outputs"])}

    def cancel(self, assignment_id: str) -> bool:
        """Remove this prompt only if still queued; never call global /interrupt."""
        key = hashlib.sha256(assignment_id.encode()).hexdigest()
        journal = self.state_root / (key + ".json")
        cancel_marker = self.state_root / (key + ".cancel")
        state = self._read_journal(journal, assignment_id)
        if not state or not state.get("prompt_id") or state.get("status") == "complete":
            return False
        try:
            _, raw, _ = self.transport.request("POST", "/queue", payload={"delete": [state["prompt_id"]]},
                                                max_bytes=64 * 1024)
            answer = json.loads(raw)
            removed = state["prompt_id"] in answer.get("deleted", [])
            if removed:
                fd = os.open(cancel_marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
            return removed
        except (ComfyUIError, ValueError, TypeError):
            return False

    def _read_journal(self, path, assignment_id):
        try:
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 128 * 1024):
                raise ComfyUIError("journal_file_invalid")
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("assignment_id") != assignment_id:
                raise ComfyUIError("journal_assignment_mismatch")
            return value
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            raise ComfyUIError("journal_unavailable") from None

    @staticmethod
    def _write_journal(path, value):
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(raw) > 128 * 1024:
            raise ComfyUIError("journal_size_exceeded")
        temp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
            dfd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _atomic_bytes(destination, data, *, mode=0o600):
        temp = destination.with_suffix(destination.suffix + ".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), mode)
        try:
            # The file is a new O_EXCL|O_NOFOLLOW inode inside the validated
            # assignment directory. Honor the caller's exact bounded mode even
            # when systemd's restrictive umask removed its group-read bit.
            os.fchmod(fd, mode)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, destination)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise


class ComfyUIOutputVerifier:
    """Reopen files and independently verify attempt, provenance, sizes and hashes."""
    REVISION = "1.0.1"
    CAPABILITY = CAPABILITY
    def __init__(self, artifact_root: str | Path, *, artifact_group_gid: int | None = None):
        self.artifact_root = Path(artifact_root)
        if artifact_group_gid is not None and (type(artifact_group_gid) is not int or artifact_group_gid <= 0):
            raise ValueError("artifact group ID must be a positive integer")
        self.artifact_group_gid = artifact_group_gid

    def verify(self, assignment, attempt, result):
        criteria = {"attempt_succeeded": attempt.get("status") == "succeeded",
                    "executor_capability_matches": attempt.get("capability") == CAPABILITY,
                    "result_digest_valid": False, "assignment_binding_valid": False,
                    "workflow_provenance_valid": False, "artifact_files_valid": False}
        evidence = [f"urn:rv:worker-attempt:{attempt.get('attempt_id', 'unknown')}"]
        try:
            encoded = json.dumps(dict(result), sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False).encode()
            criteria["result_digest_valid"] = hashlib.sha256(encoded).hexdigest() == attempt.get("result_sha256")
            criteria["assignment_binding_valid"] = (
                result.get("artifact_schema") == SCHEMA and
                result.get("assignment_id") == str(assignment.get("id")))
            criteria["workflow_provenance_valid"] = (
                isinstance(result.get("workflow_id"), str) and
                re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", result["workflow_id"]) is not None and
                isinstance(result.get("workflow_revision"), str) and
                re.fullmatch(r"[0-9a-f]{64}", result.get("template_sha256", "")) is not None and
                isinstance(result.get("prompt_id"), str))
            records = result.get("artifacts")
            valid = isinstance(records, list) and 1 <= len(records) <= MAX_OUTPUTS
            total = 0
            root_info = self.artifact_root.lstat()
            root_mode = 0o2750 if self.artifact_group_gid is not None else 0o700
            directory_mode = 0o2750 if self.artifact_group_gid is not None else 0o700
            file_mode = 0o640 if self.artifact_group_gid is not None else 0o600
            valid = bool(valid and stat.S_ISDIR(root_info.st_mode) and
                         root_info.st_uid == os.geteuid() and stat.S_IMODE(root_info.st_mode) == root_mode and
                         (self.artifact_group_gid is None or root_info.st_gid == self.artifact_group_gid) and
                         self.artifact_root.resolve() == self.artifact_root.absolute())
            expected_dir = hashlib.sha256(str(assignment["id"]).encode()).hexdigest()
            for index, item in enumerate(records if isinstance(records, list) else []):
                name = item.get("name") if isinstance(item, dict) else None
                storage_name = item.get("storage_name") if isinstance(item, dict) else None
                expected_name_hash = hashlib.sha256(name.encode()).hexdigest()[:12] if isinstance(name, str) else ""
                if (not isinstance(name, str) or not re.fullmatch(r"comfyui-output-[1-8]\.(png|jpg|webp)", name) or
                        not name.startswith(f"comfyui-output-{index + 1}.") or
                        storage_name != f"{expected_dir}/{expected_name_hash}"):
                    valid = False
                    continue
                path = self.artifact_root / storage_name
                parent_fd = os.open(self.artifact_root / expected_dir,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
                try:
                    parent_stat = os.fstat(parent_fd)
                    fd = os.open(storage_name.split("/")[1], os.O_RDONLY |
                                 getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
                    try:
                        info = os.fstat(fd)
                        data = os.read(fd, MAX_IMAGE_BYTES + 1)
                    finally:
                        os.close(fd)
                finally:
                    os.close(parent_fd)
                media = ComfyUIAction._image_type(data)
                total += len(data)
                valid = bool(valid and stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
                             stat.S_ISDIR(parent_stat.st_mode) and parent_stat.st_uid == os.geteuid() and
                             stat.S_IMODE(parent_stat.st_mode) == directory_mode and
                             stat.S_IMODE(info.st_mode) == file_mode and
                             (self.artifact_group_gid is None or
                              (parent_stat.st_gid == self.artifact_group_gid and info.st_gid == self.artifact_group_gid)) and
                             0 < len(data) <= MAX_IMAGE_BYTES and
                             media == item.get("media_type") and len(data) == item.get("bytes") and
                             hashlib.sha256(data).hexdigest() == item.get("sha256"))
                evidence.append(path.resolve().as_uri())
            first = records[0] if isinstance(records, list) and records else {}
            criteria["artifact_files_valid"] = bool(valid and total <= MAX_TOTAL_IMAGE_BYTES and
                result.get("artifact_name") == first.get("storage_name") and
                result.get("artifact_path") == str(self.artifact_root / first.get("storage_name", "")) and
                result.get("artifact_sha256") == first.get("sha256") and
                result.get("artifact_bytes") == first.get("bytes"))
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            pass
        accepted = all(criteria.values())
        return VerificationResult(VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, tuple(evidence), self.REVISION,
            "ComfyUI output artifacts independently verified" if accepted else
            "ComfyUI output artifact verification failed")

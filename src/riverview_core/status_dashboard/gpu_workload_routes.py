"""Steward-only API adapter for the fixed OCTOMINER1 workload controller."""
# Revision: 1.0.0
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4


HOST = "192.168.1.160"
SCOPE = "host:octominer1"
KEY = Path("/etc/riverview/gpu-workload-control/id_ed25519")
KNOWN_HOSTS_CREDENTIAL = "resource-telemetry-known-hosts"
BASE = "/api/v1/hardware/workloads"
JOB = re.compile(r"^/api/v1/hardware/workloads/jobs/([0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$")
START = {"comfyui": "start_comfyui", "vision": "start_vision"}
STOP = {"comfyui": "stop_comfyui", "vision": "stop_vision"}
SWITCH = {"comfyui": "switch_to_comfyui", "vision": "switch_to_vision"}
OP_ACTION = {"read": "hardware.gpu.workload.read",
             "start": "hardware.gpu.workload.start",
             "stop": "hardware.gpu.workload.stop",
             "switch": "hardware.gpu.workload.switch"}


def is_route(method: str, path: str) -> bool:
    return ((method in {"GET", "HEAD"} and (path == BASE or JOB.fullmatch(path) is not None)) or
            (method == "POST" and path in {BASE + "/start", BASE + "/stop", BASE + "/switch"}))


def _authority_context(handler):
    identity = getattr(handler, "_account_identity", None)
    if (not getattr(handler, "_account_cookie_authenticated", False) or not identity or
            "steward" not in identity.get("roles", ()) or
            identity.get("authority_principal_id") != "steward:camrui"):
        return None
    operations = getattr(handler.server, "_comms5_operations", None)
    registry = getattr(operations, "authority_registry", None) if operations else None
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
    token_path = Path(credential_dir) / "authority-steward-token" if credential_dir else None
    if registry is None or token_path is None or token_path.is_symlink() or not token_path.is_file():
        raise RuntimeError("authority_service_unavailable")
    if token_path.resolve().parent != Path(credential_dir).resolve():
        raise RuntimeError("authority_credential_path_invalid")
    token = token_path.read_text(encoding="ascii").strip()
    return identity, registry, token


def _has_authority(registry, token, action: str) -> bool:
    try:
        result = registry.authorize(token, action, SCOPE)
    except Exception as exc:
        from riverview_core.institutional_authority.registry import AuthorityDenied
        if isinstance(exc, AuthorityDenied):
            return False
        raise RuntimeError("authority_service_unavailable") from None
    return result.get("principal_id") == "steward:camrui" and result.get("principal_kind") == "steward"


def _controller() -> "GpuWorkloadRemote":
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
    known_hosts = Path(credential_dir) / KNOWN_HOSTS_CREDENTIAL if credential_dir else None
    if (KEY.is_symlink() or not KEY.is_file() or KEY.stat().st_mode & 0o027 or
            known_hosts is None or known_hosts.is_symlink() or not known_hosts.is_file()):
        raise RuntimeError("gpu_control_transport_unavailable")
    return GpuWorkloadRemote(KEY, known_hosts)


class GpuWorkloadRemote:
    """Pinned-host, forced-command SSH client; no shell or caller-defined target."""
    def __init__(self, key: Path, known_hosts: Path, *, runner=subprocess.run):
        self.key, self.known_hosts, self.runner = key, known_hosts, runner

    def call(self, command: str) -> dict:
        if command != "status" and not re.fullmatch(
                r"(?:job:[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|submit:(?:start_comfyui|stop_comfyui|switch_to_comfyui|start_vision|stop_vision|switch_to_vision):[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}:steward:camrui)", command):
            raise ValueError("gpu_control_command_not_allowlisted")
        args = ["/usr/bin/ssh", "-T", "-p", "22", "-i", str(self.key),
                "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={self.known_hosts}",
                "-o", "GlobalKnownHostsFile=/dev/null", "-o", "ConnectTimeout=3",
                "-o", "ServerAliveInterval=3", "-o", "ServerAliveCountMax=1",
                "-o", "LogLevel=ERROR", f"root@{HOST}", command]
        try:
            result = self.runner(args, check=False, capture_output=True, text=True,
                                 timeout=7, env={"LC_ALL": "C"})
        except (OSError, subprocess.SubprocessError):
            raise RuntimeError("gpu_control_transport_failed") from None
        if result.returncode != 0 or len(result.stdout.encode("utf-8")) > 8192:
            raise RuntimeError("gpu_control_remote_unavailable")
        try:
            payload = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise RuntimeError("gpu_control_response_invalid") from None
        if not isinstance(payload, dict):
            raise RuntimeError("gpu_control_response_invalid")
        return payload


def dispatch(handler, parsed, request_id):
    if not is_route(handler.command, parsed.path):
        return False
    if handler.command in {"GET", "HEAD"} and parsed.query:
        handler._error(400, "gpu_control_query_invalid", request_id)
        return True
    action = "read"
    service = None
    if handler.command == "POST":
        action = parsed.path.rsplit("/", 1)[-1]
    try:
        context = _authority_context(handler)
        if context is None:
            handler._error(403, "steward_gpu_workload_authority_required", request_id)
            return True
        identity, registry, token = context
        permissions = {key: _has_authority(registry, token, capability)
                       for key, capability in OP_ACTION.items()}
        if not permissions[action]:
            handler._error(403, "steward_gpu_workload_authority_required", request_id)
            return True
        controller = _controller()
        if handler.command in {"GET", "HEAD"}:
            match = JOB.fullmatch(parsed.path)
            result = controller.call("job:" + match.group(1)) if match else controller.call("status")
            if not match:
                result["permissions"] = permissions
            status = 200 if "error" not in result else 404
            handler._json(status, result, request_id)
            return True
        data = handler._json_body(1024)
        if set(data) != {"service"} or data.get("service") not in {"comfyui", "vision"}:
            handler._error(400, "gpu_workload_operation_invalid", request_id)
            return True
        table = {"start": START, "stop": STOP, "switch": SWITCH}[action]
        op = table[data["service"]]
        actor = identity["authority_principal_id"]
        job_id = str(uuid4())
        result = controller.call(f"submit:{op}:{job_id}:{actor}")
        if result.get("job_id") != job_id or result.get("state") != "queued":
            handler._error(503, "gpu_workload_submission_failed", request_id)
            return True
        handler._json(202, {"job_id": job_id, "state": "queued", "operation": op}, request_id)
        return True
    except PermissionError:
        handler._error(403, "steward_gpu_workload_authority_required", request_id)
    except Exception as exc:
        code = str(exc) if str(exc).startswith(("gpu_", "authority_")) else "gpu_workload_control_unavailable"
        handler._error(503, code, request_id)
    return True

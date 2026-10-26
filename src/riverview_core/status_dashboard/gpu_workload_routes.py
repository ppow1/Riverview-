"""Steward-only API adapter for registered GPU workload controllers."""
# Revision: 2.0.0
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qs
from uuid import uuid4


BASE = "/api/v1/hardware/workloads"
JOB = re.compile(r"^/api/v1/hardware/workloads/jobs/([0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$")
HOST_ID = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
REMOTE_OPERATIONS = {"start_comfyui", "stop_comfyui", "switch_to_comfyui",
                     "start_vision", "stop_vision", "switch_to_vision"}
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
    registry = getattr(handler.server, "_authority_registry", None)
    if registry is None:
        operations = getattr(handler.server, "_comms5_operations", None)
        registry = getattr(operations, "authority_registry", None) if operations else None
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
    token_path = Path(credential_dir) / "authority-steward-token" if credential_dir else None
    if registry is None or token_path is None or token_path.is_symlink() or not token_path.is_file():
        raise RuntimeError("authority_service_unavailable")
    if token_path.resolve().parent != Path(credential_dir).resolve():
        raise RuntimeError("authority_credential_path_invalid")
    return identity, registry, token_path.read_text(encoding="ascii").strip()


def _authorization(registry, token: str, action: str, host_id: str) -> dict:
    try:
        result = registry.authorize(token, action, f"host:{host_id}")
    except Exception as exc:
        from riverview_core.institutional_authority.registry import AuthorityDenied
        if isinstance(exc, AuthorityDenied):
            result = None
        else:
            raise RuntimeError("authority_service_unavailable") from None
    if result is not None:
        if result.get("principal_id") == "steward:camrui" and result.get("principal_kind") == "steward":
            return {"allowed":True,"mode":"direct","grant":None}
        return {"allowed":False,"mode":None,"grant":None}
    delegated_list = getattr(registry,"list_active_delegated_grants",None)
    if callable(delegated_list):
        grants = delegated_list(token,action,f"host:{host_id}")
        grant = next((item for item in grants if item.get("policy_ref")=="policy:delegation.v1"),None)
        if grant:
            return {"allowed":True,"mode":"delegated","grant":grant}
    return {"allowed":False,"mode":None,"grant":None}


def _has_authority(registry, token: str, action: str, host_id: str) -> bool:
    try:
        return _authorization(registry,token,action,host_id)["allowed"]
    except Exception as exc:
        raise RuntimeError("authority_service_unavailable") from None


def _registrations(handler) -> dict:
    telemetry = getattr(handler.server, "_resource_telemetry", None)
    if telemetry is None or not callable(getattr(telemetry, "workload_controller_registrations", None)):
        raise RuntimeError("hardware_host_registry_unavailable")
    return telemetry.workload_controller_registrations()


def _verified_hosts(handler) -> dict:
    telemetry = getattr(handler.server, "_resource_telemetry", None)
    if telemetry is None or not callable(getattr(telemetry, "read", None)):
        raise RuntimeError("hardware_host_registry_unavailable")
    result = telemetry.read()
    if not isinstance(result, dict) or not isinstance(result.get("hosts"), list):
        raise RuntimeError("hardware_host_registry_unavailable")
    return {item.get("host_id"): item for item in result["hosts"] if isinstance(item, dict)}


def _registration(handler, host_id: str, registrations=None, hosts=None) -> dict:
    if not isinstance(host_id, str) or not HOST_ID.fullmatch(host_id):
        raise ValueError("gpu_host_id_invalid")
    registrations = registrations if registrations is not None else _registrations(handler)
    hosts = hosts if hosts is not None else _verified_hosts(handler)
    registration = registrations.get(host_id)
    host = hosts.get(host_id)
    if not isinstance(registration, dict):
        raise LookupError("gpu_controller_not_registered")
    if not isinstance(host, dict) or host.get("identity_state") != "verified":
        raise LookupError("gpu_host_identity_unverified")
    services = registration.get("services")
    if not isinstance(services, list) or not services:
        raise RuntimeError("gpu_controller_services_unavailable")
    return registration


def _controller(registration: dict) -> "GpuWorkloadRemote":
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
    key = Path(registration["private_key_path"])
    known_hosts_name = registration["known_hosts_credential"]
    known_hosts = Path(credential_dir) / known_hosts_name if credential_dir else None
    if (key.is_symlink() or not key.is_file() or key.stat().st_mode & 0o027 or
            known_hosts is None or known_hosts.is_symlink() or not known_hosts.is_file()):
        raise RuntimeError("gpu_control_transport_unavailable")
    if known_hosts.resolve().parent != Path(credential_dir).resolve():
        raise RuntimeError("gpu_control_transport_unavailable")
    return GpuWorkloadRemote(registration, key, known_hosts)


class GpuWorkloadRemote:
    """Pinned-host, forced-command SSH client; only registered host metadata is used."""
    def __init__(self, registration: dict, key: Path, known_hosts: Path, *, runner=subprocess.run):
        self.registration, self.key, self.known_hosts, self.runner = registration, key, known_hosts, runner

    def call(self, command: str) -> dict:
        match = re.fullmatch(
            r"(?:status|job:[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|"
            r"submit:(?:start_comfyui|stop_comfyui|switch_to_comfyui|start_vision|stop_vision|switch_to_vision):"
            r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}:steward:camrui)", command)
        if not match:
            raise ValueError("gpu_control_command_not_allowlisted")
        args = ["/usr/bin/ssh", "-T", "-p", str(self.registration["transport_port"]),
                "-i", str(self.key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={self.known_hosts}",
                "-o", "GlobalKnownHostsFile=/dev/null", "-o", "ConnectTimeout=3",
                "-o", "ServerAliveInterval=3", "-o", "ServerAliveCountMax=1",
                "-o", "LogLevel=ERROR",
                f"{self.registration['transport_user']}@{self.registration['transport_host']}", command]
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


def _service(registration: dict, service_id: str) -> dict:
    for service in registration.get("services", []):
        if isinstance(service, dict) and service.get("service_id") == service_id:
            if service.get("controller_service") not in {"vision", "comfyui"}:
                break
            return service
    raise ValueError("gpu_workload_service_not_registered")


def _host_payload(host: dict, registration: dict | None, permissions=None, status=None) -> dict:
    verified = host.get("identity_state") == "verified"
    control_state = "registered" if registration and verified else (
        "unverified_host" if registration else "not_registered")
    return {"host_id": host.get("host_id"), "display_name": host.get("display_name"),
            "identity_state": host.get("identity_state"),
            "controller_state": control_state,
            "controller_id": registration.get("controller_id") if registration and verified else None,
            "services": (status or {}).get("services", {}),
            "queues": (status or {}).get("queues", {}),
            "service_catalog": registration.get("services", []) if registration else [],
            "gpu": (status or {}).get("gpu"), "observed_at": (status or {}).get("observed_at"),
            "active_job": (status or {}).get("active_job"), "permissions": permissions or {},
            "capabilities": registration.get("capabilities", []) if registration and verified else []}


def dispatch(handler, parsed, request_id):
    if not is_route(handler.command, parsed.path):
        return False
    query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=2)
    if set(query) - {"host_id"} or any(len(values) != 1 for values in query.values()):
        handler._error(400, "gpu_control_query_invalid", request_id)
        return True
    try:
        context = _authority_context(handler)
        if context is None:
            handler._error(403, "steward_gpu_workload_authority_required", request_id)
            return True
        identity, registry, token = context
        registrations = _registrations(handler)
        hosts = _verified_hosts(handler)
        if handler.command in {"GET", "HEAD"} and parsed.path == BASE and "host_id" not in query:
            rows = []
            any_read = False
            for host in hosts.values():
                host_id = host.get("host_id")
                registration = registrations.get(host_id)
                if not registration:
                    rows.append(_host_payload(host, None))
                    continue
                if host.get("identity_state") != "verified":
                    rows.append(_host_payload(host, registration))
                    continue
                permissions = {name: _has_authority(registry, token, capability, host_id)
                               for name, capability in OP_ACTION.items()}
                status = None
                if permissions["read"]:
                    any_read = True
                    status = _controller(registration).call("status")
                rows.append(_host_payload(host, registration, permissions, status))
            if not any_read:
                handler._error(403, "steward_gpu_workload_authority_required", request_id)
                return True
            handler._json(200, {"hosts": rows}, request_id)
            return True
        host_id = query.get("host_id", [None])[0]
        if handler.command in {"GET", "HEAD"}:
            job_match = JOB.fullmatch(parsed.path)
            action = "read"
            if host_id is None:
                handler._error(400, "gpu_host_id_required", request_id)
                return True
            registration = _registration(handler, host_id, registrations, hosts)
            if not _has_authority(registry, token, OP_ACTION[action], host_id):
                handler._error(403, "steward_gpu_workload_authority_required", request_id)
                return True
            command = "job:" + job_match.group(1) if job_match else "status"
            result = _controller(registration).call(command)
            if job_match and result.get("state") in {"succeeded", "failed"}:
                operation_name = result.get("operation", "")
                operation_action = ("switch" if operation_name.startswith("switch_to_") else
                                    operation_name.split("_",1)[0] if operation_name else "")
                if operation_action in {"start","stop","switch"}:
                    granted = _authorization(registry,token,OP_ACTION[operation_action],host_id)
                    if granted["mode"] == "delegated":
                        operation_ref=f"gpu-workload:{host_id}:{job_match.group(1)}"
                        reservation=registry.reserve_delegated_grant(token,granted["grant"]["grant_id"],
                            OP_ACTION[operation_action],f"host:{host_id}",operation_ref,
                            idempotency_key=job_match.group(1))
                        if result.get("state")=="succeeded":
                            registry.consume_delegated_grant(token,reservation["reservation_id"],
                                f"gpu-workload-job:{job_match.group(1)}:succeeded")
                        else:
                            registry.release_delegated_grant(token,reservation["reservation_id"],
                                "gpu_operation_failed")
            if not job_match:
                result["host_id"] = host_id
                result["permissions"] = {name: _has_authority(registry, token, capability, host_id)
                                         for name, capability in OP_ACTION.items()}
                result["service_catalog"] = registration["services"]
            handler._json(200 if "error" not in result else 404, result, request_id)
            return True
        action = parsed.path.rsplit("/", 1)[-1]
        if query:
            handler._error(400, "gpu_control_query_invalid", request_id)
            return True
        data = handler._json_body(1024)
        host_id = data.get("host_id") if isinstance(data, dict) else None
        registration = _registration(handler, host_id, registrations, hosts)
        auth = _authorization(registry, token, OP_ACTION[action], host_id)
        if not auth["allowed"]:
            handler._error(403, "steward_gpu_workload_authority_required", request_id)
            return True
        if (not isinstance(data, dict) or set(data) != {"host_id", "service"} or
                data.get("host_id") != host_id or not isinstance(data.get("service"), str)):
            handler._error(400, "gpu_workload_operation_invalid", request_id)
            return True
        service = _service(registration, data["service"])
        alias = service["controller_service"]
        operation = {"start": f"start_{alias}", "stop": f"stop_{alias}",
                     "switch": f"switch_to_{alias}"}[action]
        if operation not in REMOTE_OPERATIONS:
            handler._error(400, "gpu_workload_operation_invalid", request_id)
            return True
        job_id = str(uuid4())
        reservation = None
        if auth["mode"] == "delegated":
            operation_ref=f"gpu-workload:{host_id}:{job_id}"
            reservation=registry.reserve_delegated_grant(token,auth["grant"]["grant_id"],
                OP_ACTION[action],f"host:{host_id}",operation_ref,idempotency_key=job_id)
            if reservation.get("status")!="reserved":
                handler._error(403,"steward_gpu_workload_authority_required",request_id)
                return True
        try:
            result = _controller(registration).call(f"submit:{operation}:{job_id}:{identity['authority_principal_id']}")
        except Exception:
            if reservation:
                registry.release_delegated_grant(token,reservation["reservation_id"],"gpu_submission_failed")
            raise
        if result.get("job_id") != job_id or result.get("state") != "queued":
            if reservation:
                registry.release_delegated_grant(token,reservation["reservation_id"],"gpu_submission_failed")
            handler._error(503, "gpu_workload_submission_failed", request_id)
            return True
        handler._json(202, {"host_id": host_id, "job_id": job_id, "state": "queued",
                            "operation": operation}, request_id)
        return True
    except LookupError as exc:
        handler._error(404, str(exc), request_id)
    except PermissionError:
        handler._error(403, "steward_gpu_workload_authority_required", request_id)
    except (ValueError, TypeError):
        handler._error(400, "gpu_workload_operation_invalid", request_id)
    except Exception as exc:
        code = str(exc) if str(exc).startswith(("gpu_", "authority_", "hardware_")) else "gpu_workload_control_unavailable"
        handler._error(503, code, request_id)
    return True

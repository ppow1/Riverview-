"""Bounded Windows PowerShell/SSH command gateway for Comms5.

File Revision: 1.1.4
Component: COMMS5-WINDOWS-COMMAND-GATEWAY
Authority: Existing AuthorityRegistry grants and systemd-loaded service credential.
Changed: 2026-10-27 UTC | C2-359-CAMRUI-SSH-ADDRESS | Use the verified Camrui IP while retaining the pinned camrui host-key alias.
Changed: 2026-10-27 UTC | COMMS5-ASYNC-COMMAND-TASKS-357 | Add durable asynchronous execution, cancellation, deadlines, and recovery under existing host-scoped grants.
Changed: 2026-10-27 UTC | C2-357-COMBINED-CANCEL | Preserve bounded agent HTTP diagnostics and bind cancellation to the submitted command digest before dispatch.

Authorization remains in Riverview's AuthorityRegistry; the Windows agent
persists bounded execution records and never receives credentials from Comms5.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import ssl
import subprocess
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPSHandler
from uuid import uuid4


MAX_BODY_BYTES = 16_384
MAX_OUTPUT_BYTES = 32_768
MAX_COMMAND_CHARS = 8_000
AGENT_HTTP_TIMEOUT = 20.0
COMMAND_TIMEOUT_SECONDS = 12
COMMAND_TASK_TIMEOUT_SECONDS = 3_600
COMMAND_TASK_MAX_TIMEOUT_SECONDS = 86_400
COMMAND_TASK_INLINE_WAIT_SECONDS = 2.0
HOSTS = {
    "powershell_identity": ("desktop-ja3rpnq", "host:desktop-ja3rpnq", "standard"),
    "ssh_camrui_hostname": ("camrui", "host:camrui", "standard"),
}
TASK_HOSTS = {
    # These identifiers are fixed server-side mappings. SSH aliases must be
    # provisioned with pinned host keys on the Windows executor before use.
    "desktop-ja3rpnq": ("desktop-ja3rpnq", "host:desktop-ja3rpnq", "powershell"),
    "camrui": ("camrui", "host:camrui", "ssh"),
    "octominer1": ("octominer1", "host:octominer1", "ssh"),
    "octominer2": ("octominer2", "host:octominer2", "ssh"),
}
SSH_HOST_TARGETS = {
    "camrui": ("192.168.1.155", "camrui"),
}
TASK_PRIVILEGES = frozenset({"standard", "elevated"})
CALLER_ACTIONS = {
    name: "comms5.command.submit." + name for name in HOSTS
}
EXECUTION_ACTIONS = {
    name: "comms5.command.execute.readonly." + name + ".standard" for name in HOSTS
}
_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")


class CommandGatewayDenied(PermissionError):
    """The caller or command grant does not authorize this exact operation."""


class CommandAgentUnavailable(RuntimeError):
    """The pinned Windows agent did not provide a trustworthy response."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _bounded_text(value: object, limit: int = MAX_OUTPUT_BYTES) -> str:
    if not isinstance(value, str):
        return ""
    encoded = value.encode("utf-8", "replace")[:limit]
    return encoded.decode("utf-8", "ignore")


def _safe_operation(name: object) -> tuple[str, str, str]:
    if not isinstance(name, str) or name not in HOSTS:
        raise ValueError("command_operation_not_allowlisted")
    return HOSTS[name]


class WindowsCommandGateway:
    """Authorize and dispatch one fixed operation through AuthorityRegistry."""

    def __init__(self, *, authority_registry, authorizer, ledger_db,
                 grantee_credential: str, agent_client, command_grant_authority=None):
        if (authority_registry is None or authorizer is None or ledger_db is None or
                not isinstance(grantee_credential, str) or len(grantee_credential) < 32 or
                agent_client is None):
            raise ValueError("command_gateway_dependencies_missing")
        self.registry = authority_registry
        self.authorizer = authorizer
        self.ledger_db = ledger_db
        self.grantee_credential = grantee_credential
        self.agent = agent_client
        self.command_grant_authority = command_grant_authority

    @classmethod
    def from_environment(cls, *, authority_registry, authorizer, ledger_db,
                         command_grant_authority=None):
        credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
        if not credential_dir:
            raise RuntimeError("command_gateway_credentials_not_loaded")
        root = Path(credential_dir)
        grantee = (root / "command-gateway-grantee").read_text(encoding="ascii").strip()
        client = WindowsCommandAgentClient(
            os.environ.get("RIVERVIEW_COMMAND_AGENT_URL", "https://desktop-ja3rpnq:8443"),
            root / "command-agent-token", ca_file=root / "command-agent-ca.pem")
        return cls(authority_registry=authority_registry, authorizer=authorizer,
                   ledger_db=ledger_db, grantee_credential=grantee, agent_client=client,
                   command_grant_authority=command_grant_authority)

    @staticmethod
    def _idempotency(principal: str, operation: str, key: object) -> str:
        if not isinstance(key, str) or not _IDEMPOTENCY.fullmatch(key):
            raise ValueError("command_idempotency_key_invalid")
        digest = hashlib.sha256((principal + "\0" + operation + "\0" + key).encode()).hexdigest()
        return "cmd-" + digest

    def _authorize_caller(self, principal: str, operation: str) -> dict:
        _, scope, _ = _safe_operation(operation)
        action = CALLER_ACTIONS[operation]
        try:
            with self.ledger_db.transaction():
                with self.ledger_db.cursor() as cursor:
                    grant = self.authorizer.require_principal(cursor, principal, action, scope)
        except Exception as exc:
            if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                raise CommandGatewayDenied("caller_command_grant_denied") from None
            raise
        return grant

    def submit(self, principal: str, arguments: dict) -> dict:
        if set(arguments) != {"operation", "execution_grant_id", "idempotency_key"}:
            raise ValueError("command_submit_fields_invalid")
        operation = arguments["operation"]
        target, scope, privilege = _safe_operation(operation)
        execution_grant_id = arguments["execution_grant_id"]
        if not isinstance(execution_grant_id, str) or not 1 <= len(execution_grant_id) <= 128:
            raise ValueError("execution_grant_id_invalid")
        caller = self._authorize_caller(principal, operation)
        idem = self._idempotency(principal, operation, arguments["idempotency_key"])
        operation_ref = "comms5-command:" + idem
        execution_action = EXECUTION_ACTIONS[operation]
        try:
            reservation = self.registry.reserve_delegated_grant(
                self.grantee_credential, execution_grant_id, execution_action, scope,
                operation_ref, idempotency_key=idem)
        except Exception as exc:
            if type(exc).__name__ in {"AuthorityDenied", "RegistryUnavailable"}:
                raise CommandGatewayDenied("execution_allowance_denied") from None
            raise
        if reservation.get("status") not in {"reserved", "consumed"}:
            raise CommandGatewayDenied("execution_allowance_inactive")

        try:
            with self.ledger_db.transaction():
                with self.ledger_db.cursor() as cursor:
                    current = self.authorizer.require(cursor, self.grantee_credential,
                                                      execution_action, scope)
            if current.get("grant_id") != execution_grant_id:
                raise CommandGatewayDenied("execution_grant_changed_before_dispatch")
        except Exception as exc:
            self.registry.release_delegated_grant(
                self.grantee_credential, reservation["reservation_id"],
                "authority_revoked_before_dispatch")
            if isinstance(exc, CommandGatewayDenied):
                raise
            if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                raise CommandGatewayDenied("execution_grant_inactive_before_dispatch") from None
            raise

        request = {
            "operation": operation, "target_host": target,
            "privilege_level": privilege, "caller_principal": principal,
            "caller_grant_id": caller["grant_id"],
            "execution_grant_id": execution_grant_id,
            "reservation_id": reservation["reservation_id"],
            "idempotency_key": idem,
        }
        result = self.agent.submit(request)
        status = result.get("execution_status")
        if status == "denied":
            self.registry.release_delegated_grant(
                self.grantee_credential, reservation["reservation_id"],
                "command_agent_rejected")
        elif status in {"queued", "running", "completed", "failed", "timed_out", "cancelled", "interrupted"}:
            self.registry.consume_delegated_grant(
                self.grantee_credential, reservation["reservation_id"],
                result["execution_id"])
        else:
            raise CommandAgentUnavailable("command_agent_status_invalid")
        return self._result(result, principal, caller["grant_id"], execution_grant_id,
                            reservation["reservation_id"], operation, target, privilege)

    def status(self, principal: str, arguments: dict) -> dict:
        if set(arguments) != {"operation", "idempotency_key"}:
            raise ValueError("command_status_fields_invalid")
        operation = arguments["operation"]
        target, _, privilege = _safe_operation(operation)
        caller_grant = self._authorize_caller(principal, operation)
        idem = self._idempotency(principal, operation, arguments["idempotency_key"])
        result = self.agent.status(idem, principal, operation)
        if result.get("execution_status") == "not_found":
            return {"status": "not_found", "executed": False,
                    "authorization_evidence": {"principal_id": principal,
                        "caller_grant_id": caller_grant["grant_id"],
                        "action": CALLER_ACTIONS[operation], "scope_ref": HOSTS[operation][1]}}
        return self._result(result, principal, caller_grant["grant_id"],
                            result.get("execution_grant_id", ""),
                            result.get("reservation_id", ""), operation, target, privilege)

    @staticmethod
    def _task_target(host_id: object, privilege: object):
        if not isinstance(host_id, str) or host_id not in TASK_HOSTS:
            raise ValueError("command_host_not_registered")
        if privilege not in TASK_PRIVILEGES:
            raise ValueError("command_privilege_invalid")
        target, scope, transport = TASK_HOSTS[host_id]
        operation = "command_task_" + privilege
        return operation, target, scope, transport, privilege

    @staticmethod
    def _task_actions(host_id: str, privilege: str):
        # Caller and executor authorities are separate, exact, and host-scoped.
        return (f"comms5.command.submit.task.{host_id}.{privilege}",
                f"comms5.command.execute.task.{host_id}.{privilege}")

    def submit_task(self, principal: str, arguments: dict) -> dict:
        expected = {"host_id", "command", "privilege_level", "execution_grant_id",
                    "idempotency_key"}
        if not isinstance(arguments, dict) or set(arguments) != expected:
            raise ValueError("command_task_submit_fields_invalid")
        operation, target, scope, transport, privilege = self._task_target(
            arguments["host_id"], arguments["privilege_level"])
        if transport == "powershell" and privilege == "elevated":
            raise CommandAgentUnavailable("windows_elevated_executor_not_configured")
        command = arguments["command"]
        if (not isinstance(command, str) or not command.strip() or
                len(command.encode("utf-8")) > MAX_COMMAND_CHARS or "\x00" in command):
            raise ValueError("command_task_text_invalid")
        execution_grant_id = arguments["execution_grant_id"]
        if not isinstance(execution_grant_id, str) or not 1 <= len(execution_grant_id) <= 128:
            raise ValueError("execution_grant_id_invalid")
        caller_action, execution_action = self._task_actions(arguments["host_id"], privilege)
        if self.command_grant_authority is None:
            raise CommandGatewayDenied("protected_command_grant_authority_unavailable")
        try:
            with self.ledger_db.transaction():
                with self.ledger_db.cursor() as cursor:
                    caller = self.authorizer.require_principal(cursor, principal,
                                                               caller_action, scope)
        except Exception as exc:
            if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                raise CommandGatewayDenied("caller_command_grant_denied") from None
            raise
        idem = self._idempotency(principal, operation + ":" + arguments["host_id"],
                                 arguments["idempotency_key"])
        command_digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
        existing = self.agent.status(idem, principal, operation)
        if isinstance(existing, dict) and existing.get("execution_status") != "not_found":
            if (existing.get("command_sha256") != command_digest or
                    existing.get("host_id") != arguments["host_id"] or
                    existing.get("privilege_level") != privilege or
                    existing.get("execution_grant_id") != execution_grant_id):
                raise ValueError("idempotency_key_conflict")
            return self._result(existing, principal, caller["grant_id"], execution_grant_id,
                existing.get("reservation_id", ""), operation, target, privilege)
        operation_ref = "comms5-command:" + idem
        try:
            reservation = self.command_grant_authority.reserve_command_task_grant(
                execution_grant_id, execution_action, scope,
                operation_ref, idempotency_key=idem)
        except Exception as exc:
            if type(exc).__name__ in {"AuthorityDenied", "RegistryUnavailable"}:
                raise CommandGatewayDenied("execution_allowance_denied") from None
            raise
        if reservation.get("status") not in {"reserved", "consumed"}:
            raise CommandGatewayDenied("execution_allowance_inactive")
        try:
            with self.ledger_db.transaction():
                with self.ledger_db.cursor() as cursor:
                    current = self.authorizer.require(cursor, self.grantee_credential,
                                                      execution_action, scope)
            if current.get("grant_id") != execution_grant_id:
                raise CommandGatewayDenied("execution_grant_changed_before_dispatch")
        except Exception as exc:
            self.command_grant_authority.release_command_task_grant(
                reservation["reservation_id"], "authority_revoked_before_dispatch")
            if isinstance(exc, CommandGatewayDenied):
                raise
            if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                raise CommandGatewayDenied("execution_grant_inactive_before_dispatch") from None
            raise
        request = {"operation": operation, "target_host": target, "host_id": arguments["host_id"],
            "transport": transport, "privilege_level": privilege, "command": command,
            "caller_principal": principal, "caller_grant_id": caller["grant_id"],
            "execution_grant_id": execution_grant_id,
            "reservation_id": reservation["reservation_id"], "idempotency_key": idem}
        try:
            result = self.agent.submit(request)
        except Exception:
            self.command_grant_authority.release_command_task_grant(
                reservation["reservation_id"], "command_agent_unavailable")
            raise
        status = result.get("execution_status")
        if status == "denied":
            self.command_grant_authority.release_command_task_grant(
                reservation["reservation_id"], "command_agent_rejected")
        elif status in {"queued", "running", "completed", "failed", "timed_out", "cancelled", "interrupted"}:
            self.command_grant_authority.consume_command_task_grant(
                reservation["reservation_id"], result["execution_id"])
        else:
            raise CommandAgentUnavailable("command_agent_status_invalid")
        return self._result(result, principal, caller["grant_id"], execution_grant_id,
                            reservation["reservation_id"], operation, target, privilege)

    def task_status(self, principal: str, arguments: dict) -> dict:
        expected = {"host_id", "command_sha256", "privilege_level", "idempotency_key"}
        if not isinstance(arguments, dict) or set(arguments) != expected:
            raise ValueError("command_task_status_fields_invalid")
        operation, target, scope, _transport, privilege = self._task_target(
            arguments["host_id"], arguments["privilege_level"])
        if not isinstance(arguments["command_sha256"], str) or not re.fullmatch(
                r"[0-9a-f]{64}", arguments["command_sha256"]):
            raise ValueError("command_hash_invalid")
        caller_action, _ = self._task_actions(arguments["host_id"], privilege)
        try:
            with self.ledger_db.transaction():
                with self.ledger_db.cursor() as cursor:
                    caller = self.authorizer.require_principal(cursor, principal, caller_action, scope)
        except Exception as exc:
            if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                raise CommandGatewayDenied("caller_command_grant_denied") from None
            raise
        idem = self._idempotency(principal, operation + ":" + arguments["host_id"],
                                 arguments["idempotency_key"])
        result = self.agent.status(idem, principal, operation)
        if result.get("execution_status") == "not_found":
            return {"status": "not_found", "executed": False,
                "host_id": arguments["host_id"], "privilege_level": privilege,
                "command_sha256": arguments["command_sha256"],
                "authorization_evidence": {"principal_id": principal,
                    "caller_grant_id": caller["grant_id"], "action": caller_action,
                    "scope_ref": scope}}
        if result.get("command_sha256") != arguments["command_sha256"]:
            return {"status": "not_found", "executed": False}
        return self._result(result, principal, caller["grant_id"],
            result.get("execution_grant_id", ""), result.get("reservation_id", ""),
            operation, target, privilege)

    def cancel_task(self, principal: str, arguments: dict) -> dict:
        expected = {"host_id", "command_sha256", "privilege_level", "idempotency_key"}
        if not isinstance(arguments, dict) or set(arguments) != expected:
            raise ValueError("command_task_cancel_fields_invalid")
        operation, target, scope, _transport, privilege = self._task_target(
            arguments["host_id"], arguments["privilege_level"])
        digest = arguments["command_sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("command_hash_invalid")
        caller_action, _ = self._task_actions(arguments["host_id"], privilege)
        try:
            with self.ledger_db.transaction():
                with self.ledger_db.cursor() as cursor:
                    caller = self.authorizer.require_principal(cursor, principal,
                                                               caller_action, scope)
        except Exception as exc:
            if type(exc).__name__ in {"GrantDenied", "GrantCheckUnavailable"}:
                raise CommandGatewayDenied("caller_command_grant_denied") from None
            raise
        idem = self._idempotency(principal, operation + ":" + arguments["host_id"],
                                 arguments["idempotency_key"])
        existing = self.agent.status(idem, principal, operation)
        if (not isinstance(existing, dict) or
                existing.get("execution_status") == "not_found" or
                existing.get("command_sha256") != digest or
                existing.get("host_id") != arguments["host_id"] or
                existing.get("privilege_level") != privilege):
            return {"status": "not_found", "executed": False, "host_id": arguments["host_id"],
                    "privilege_level": privilege, "command_sha256": digest,
                    "authorization_evidence": {"principal_id": principal,
                        "caller_grant_id": caller["grant_id"], "action": caller_action,
                        "scope_ref": scope}}
        result = self.agent.cancel(idem, principal, operation)
        if (not isinstance(result, dict) or result.get("execution_status") == "not_found" or
                result.get("command_sha256") != digest or
                result.get("host_id") != arguments["host_id"] or
                result.get("privilege_level") != privilege):
            return {"status": "not_found", "executed": False, "host_id": arguments["host_id"],
                    "privilege_level": privilege, "command_sha256": digest,
                    "authorization_evidence": {"principal_id": principal,
                        "caller_grant_id": caller["grant_id"], "action": caller_action,
                        "scope_ref": scope}}
        return self._result(result, principal, caller["grant_id"],
            result.get("execution_grant_id", ""), result.get("reservation_id", ""),
            operation, target, privilege)

    @staticmethod
    def _result(result, principal, caller_grant_id, execution_grant_id,
                reservation_id, operation, target, privilege):
        if operation.startswith("command_task_"):
            host_id = result.get("host_id", "")
            action = f"comms5.command.execute.task.{host_id}.{privilege}"
            scope = TASK_HOSTS.get(host_id, (target, "", ""))[1]
        else:
            host_id = ""
            action = EXECUTION_ACTIONS[operation]
            scope = HOSTS[operation][1]
        value = {
            "status": result["execution_status"], "executed": result["execution_status"] in
                {"queued", "running", "completed", "failed", "timed_out", "cancelled", "interrupted"},
            "execution_id": result["execution_id"],
            "operation": operation, "target_host": target,
            "privilege_level": privilege,
            "stdout": _bounded_text(result.get("stdout", "")),
            "stderr": _bounded_text(result.get("stderr", "")),
            "exit_code": result.get("exit_code"),
            "started_at": result.get("started_at"), "completed_at": result.get("completed_at"),
            "deadline_at": result.get("deadline_at"),
            "authorization_evidence": {
                "principal_id": principal, "caller_grant_id": caller_grant_id,
                "execution_grant_id": execution_grant_id,
                "action": action,
                "scope_ref": scope, "reservation_id": reservation_id,
                "reservation_status": "consumed" if result["execution_status"] != "denied" else "released",
            },
            "audit_evidence": {"execution_id": result["execution_id"],
                "audit_event_id": result.get("audit_event_id"),
                "idempotency_key": result.get("idempotency_key")},
        }
        if host_id:
            value["host_id"] = host_id
            value["task_id"] = result["execution_id"]
            value["command_sha256"] = result.get("command_sha256", "")
        return value


class WindowsCommandAgentClient:
    """HTTPS client for the Windows agent; URL and credentials are server config only."""

    def __init__(self, base_url: str, token_file: str | Path, *, ca_file: str | Path,
                 timeout: float = AGENT_HTTP_TIMEOUT):
        parsed = urlsplit(base_url)
        if (parsed.scheme != "https" or parsed.hostname != "desktop-ja3rpnq" or
                parsed.port != 8443 or parsed.path not in {"", "/"} or
                parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("command_agent_url_must_be_pinned_https_desktop")
        if not 1 <= float(timeout) <= 30:
            raise ValueError("command_agent_timeout_out_of_range")
        token = Path(token_file).read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
            raise ValueError("command_agent_credential_invalid")
        context = ssl.create_default_context(cafile=str(ca_file))
        self.url = f"{parsed.scheme}://{parsed.netloc}"
        self.token = token
        self.timeout = float(timeout)
        self.opener = build_opener(HTTPSHandler(context=context))

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = _canonical_json(body) if body is not None else None
        request = Request(self.url + path, data=data, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                if response.status not in {200, 201} or response.headers.get_content_type() != "application/json":
                    raise CommandAgentUnavailable("command_agent_http_status")
                payload = response.read(MAX_BODY_BYTES + 1)
        except HTTPError as exc:
            try:
                value = json.loads(exc.read(4096))
                code = value.get("error") if isinstance(value, dict) else None
            except Exception:
                code = None
            if not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code):
                code = "unclassified_agent_error"
            status = exc.code if isinstance(exc.code, int) and 400 <= exc.code <= 599 else 0
            raise CommandAgentUnavailable(
                f"command_agent_http_{status}_{code}") from None
        except (URLError, TimeoutError, OSError):
            raise CommandAgentUnavailable("command_agent_unavailable") from None
        if len(payload) > MAX_BODY_BYTES:
            raise CommandAgentUnavailable("command_agent_response_too_large")
        try:
            value = json.loads(payload)
        except (UnicodeError, json.JSONDecodeError):
            raise CommandAgentUnavailable("command_agent_response_invalid") from None
        if not isinstance(value, dict):
            raise CommandAgentUnavailable("command_agent_response_invalid")
        return value

    def submit(self, request: dict) -> dict:
        return self._request("POST", "/v1/commands", request)

    def status(self, idempotency_key: str, principal: str, operation: str) -> dict:
        query = urlencode({"principal": principal, "operation": operation})
        return self._request("GET", "/v1/commands/by-key/" + quote(idempotency_key, safe="")
                             + "?" + query)

    def cancel(self, idempotency_key: str, principal: str, operation: str) -> dict:
        query = urlencode({"principal": principal, "operation": operation})
        return self._request("DELETE", "/v1/commands/by-key/" + quote(idempotency_key, safe="")
                             + "?" + query)


class CommandCancelled(RuntimeError):
    def __init__(self, stdout="", stderr=""):
        super().__init__("command_cancelled")
        self.stdout = stdout
        self.stderr = stderr


class WindowsCommandAgentStore:
    """Durable task queue and result ledger; authority remains in the gateway."""

    TERMINAL = frozenset({"completed", "failed", "timed_out", "cancelled", "interrupted"})

    def __init__(self, path: str | Path, *, runner=None, timeout_seconds=COMMAND_TIMEOUT_SECONDS,
                 task_timeout_seconds=COMMAND_TASK_TIMEOUT_SECONDS,
                 inline_wait_seconds=COMMAND_TASK_INLINE_WAIT_SECONDS,
                 retention_days=30, max_queued_tasks=100,
                 output_limit=MAX_OUTPUT_BYTES):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.runner = runner or _run_windows_operation
        self.timeout_seconds = int(timeout_seconds)
        self.task_timeout_seconds = int(task_timeout_seconds)
        self.inline_wait_seconds = float(inline_wait_seconds)
        self.retention_days = int(retention_days)
        self.max_queued_tasks = int(max_queued_tasks)
        self.output_limit = int(output_limit)
        if (not 1 <= self.timeout_seconds <= 30 or
                not 1 <= self.task_timeout_seconds <= COMMAND_TASK_MAX_TIMEOUT_SECONDS or
                not 0 <= self.inline_wait_seconds < AGENT_HTTP_TIMEOUT or
                not 1 <= self.retention_days <= 365 or not 1 <= self.max_queued_tasks <= 10_000 or
                not 256 <= self.output_limit <= 65_536):
            raise ValueError("command_agent_bounds_invalid")
        self._condition = threading.Condition()
        self._pending: dict[str, dict] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._closing = False
        self._initialize()
        self._worker = threading.Thread(target=self._worker_loop,
                                        name="riverview-command-worker", daemon=True)
        self._worker.start()

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialize(self):
        with closing(self._connect()) as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                CREATE TABLE IF NOT EXISTS command_executions (
                    execution_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_sha256 TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    target_host TEXT NOT NULL,
                    host_id TEXT NOT NULL DEFAULT '',
                    transport TEXT NOT NULL DEFAULT '',
                    command_sha256 TEXT NOT NULL DEFAULT '',
                    privilege_level TEXT NOT NULL,
                    caller_principal TEXT NOT NULL,
                    caller_grant_id TEXT NOT NULL,
                    execution_grant_id TEXT NOT NULL,
                    reservation_id TEXT NOT NULL,
                    execution_status TEXT NOT NULL,
                    stdout TEXT NOT NULL DEFAULT '',
                    stderr TEXT NOT NULL DEFAULT '',
                    exit_code INTEGER,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    audit_event_id TEXT NOT NULL,
                    job_timeout_seconds INTEGER NOT NULL DEFAULT 12,
                    deadline_at TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS command_execution_events (
                    audit_event_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(execution_id) REFERENCES command_executions(execution_id)
                );
                CREATE INDEX IF NOT EXISTS command_execution_events_by_execution
                    ON command_execution_events(execution_id, occurred_at);
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(command_executions)")}
            additions = (("host_id", "TEXT NOT NULL DEFAULT ''"),
                         ("transport", "TEXT NOT NULL DEFAULT ''"),
                         ("command_sha256", "TEXT NOT NULL DEFAULT ''"),
                         ("job_timeout_seconds", "INTEGER NOT NULL DEFAULT 12"),
                         ("deadline_at", "TEXT"),
                         ("cancel_requested", "INTEGER NOT NULL DEFAULT 0"))
            for name, definition in additions:
                if name not in columns:
                    db.execute(f"ALTER TABLE command_executions ADD COLUMN {name} {definition}")
            db.execute("BEGIN IMMEDIATE")
            unfinished = db.execute("SELECT execution_id,execution_status FROM command_executions "
                                    "WHERE execution_status IN ('queued','running')").fetchall()
            for row in unfinished:
                self._event(db, row["execution_id"], "interrupted", {
                    "reason": "agent_restarted", "previous_status": row["execution_status"]})
                db.execute("UPDATE command_executions SET execution_status='interrupted',completed_at=? "
                           "WHERE execution_id=?", (_now(), row["execution_id"]))
            db.commit()
            self._purge_expired(db)

    def _purge_expired(self, db):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        expired = db.execute("SELECT execution_id FROM command_executions WHERE completed_at IS NOT NULL "
                             "AND completed_at < ? AND execution_status IN "
                             "('completed','failed','timed_out','cancelled','interrupted')",
                             (cutoff,)).fetchall()
        for row in expired:
            db.execute("DELETE FROM command_execution_events WHERE execution_id=?", (row[0],))
            db.execute("DELETE FROM command_executions WHERE execution_id=?", (row[0],))

    @staticmethod
    def _event(db, execution_id: str, event_type: str, payload: dict) -> str:
        event_id = str(uuid4())
        db.execute("INSERT INTO command_execution_events VALUES(?,?,?,?,?)",
                   (event_id, execution_id, event_type,
                    _canonical_json(payload).decode("ascii"), _now()))
        db.execute("UPDATE command_executions SET audit_event_id=? WHERE execution_id=?",
                   (event_id, execution_id))
        return event_id

    def submit(self, request: dict) -> dict:
        validated = _validate_agent_request(request)
        request_hash = hashlib.sha256(_canonical_json(validated)).hexdigest()
        is_task = validated["operation"].startswith("command_task_")
        job_timeout = self.task_timeout_seconds if is_task else self.timeout_seconds
        now_dt = datetime.now(timezone.utc)
        created = now_dt.isoformat()
        deadline = (now_dt + timedelta(seconds=job_timeout)).isoformat()
        with self._condition:
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT * FROM command_executions WHERE idempotency_key=?",
                                 (validated["idempotency_key"],)).fetchone()
                if row:
                    if row["request_sha256"] != request_hash:
                        db.rollback()
                        raise ValueError("idempotency_key_conflict")
                    db.commit()
                    execution_id = row["execution_id"]
                else:
                    queued = db.execute("SELECT COUNT(*) FROM command_executions "
                                        "WHERE execution_status IN ('queued','running')").fetchone()[0]
                    if queued >= self.max_queued_tasks:
                        db.rollback()
                        raise CommandAgentUnavailable("command_queue_full")
                    execution_id = str(uuid4())
                    event_id = str(uuid4())
                    db.execute("""INSERT INTO command_executions
                        (execution_id,idempotency_key,request_sha256,operation,target_host,host_id,
                         transport,command_sha256,privilege_level,caller_principal,caller_grant_id,
                         execution_grant_id,reservation_id,execution_status,created_at,audit_event_id,
                         job_timeout_seconds,deadline_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'queued',?,?,?,?)""",
                        (execution_id, validated["idempotency_key"], request_hash,
                         validated["operation"], validated["target_host"], validated.get("host_id", ""),
                         validated.get("transport", ""), validated.get("command_sha256", ""),
                         validated["privilege_level"], validated["caller_principal"],
                         validated["caller_grant_id"], validated["execution_grant_id"],
                         validated["reservation_id"], created, event_id, job_timeout, deadline))
                    event_payload = {key: validated.get(key, "") for key in (
                        "operation", "target_host", "host_id", "transport", "command_sha256",
                        "privilege_level", "caller_principal", "caller_grant_id",
                        "execution_grant_id", "reservation_id")}
                    db.execute("INSERT INTO command_execution_events VALUES(?,?,?,?,?)",
                               (event_id, execution_id, "accepted",
                                _canonical_json(event_payload).decode("ascii"), created))
                    db.commit()
                    # The command remains only in memory; durable records retain its digest.
                    self._pending[execution_id] = validated
                    self._condition.notify_all()
        return self._wait_for_result(execution_id, validated["idempotency_key"],
                                     validated["caller_principal"], validated["operation"])

    def _wait_for_result(self, execution_id, key, principal, operation):
        deadline = time.monotonic() + self.inline_wait_seconds
        while True:
            result = self.get_by_idempotency(key, principal, operation)
            if result.get("execution_status") in self.TERMINAL or time.monotonic() >= deadline:
                return result
            with self._condition:
                self._condition.wait(timeout=min(0.05, max(0, deadline - time.monotonic())))

    def _worker_loop(self):
        while True:
            with self._condition:
                if self._closing:
                    return
                item = self._claim_next()
                if item is None:
                    self._condition.wait()
                    continue
            self._execute(*item)

    def _claim_next(self):
        while True:
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT * FROM command_executions WHERE execution_status='queued' "
                                 "ORDER BY created_at,execution_id LIMIT 1").fetchone()
                if row is None:
                    db.commit()
                    return None
                payload = self._pending.pop(row["execution_id"], None)
                if payload is None:
                    self._event(db, row["execution_id"], "interrupted",
                                {"reason": "queued_payload_unavailable"})
                    db.execute("UPDATE command_executions SET execution_status='interrupted',completed_at=? "
                               "WHERE execution_id=?", (_now(), row["execution_id"]))
                    db.commit()
                    self._condition.notify_all()
                    continue
                now = _now()
                if row["deadline_at"] and row["deadline_at"] <= now:
                    self._event(db, row["execution_id"], "timed_out",
                                {"reason": "deadline_elapsed_in_queue"})
                    db.execute("UPDATE command_executions SET execution_status='timed_out',completed_at=?,exit_code=NULL "
                               "WHERE execution_id=?", (now, row["execution_id"]))
                    db.commit()
                    self._condition.notify_all()
                    continue
                self._event(db, row["execution_id"], "started", {"operation": payload["operation"]})
                db.execute("UPDATE command_executions SET execution_status='running',started_at=? "
                           "WHERE execution_id=?", (now, row["execution_id"]))
                db.commit()
                cancel_event = threading.Event()
                self._cancel_events[row["execution_id"]] = cancel_event
                return row["execution_id"], payload, int(row["job_timeout_seconds"]), cancel_event

    def _execute(self, execution_id, payload, timeout, cancel_event):
        try:
            if payload["operation"].startswith("command_task_"):
                runner_input = dict(payload)
                runner_input["_cancel_event"] = cancel_event
            else:
                runner_input = payload["operation"]
            stdout, stderr, exit_code = self.runner(runner_input, timeout)
            status = "cancelled" if cancel_event.is_set() else ("completed" if exit_code == 0 else "failed")
            if status == "cancelled":
                exit_code = None
        except CommandCancelled as exc:
            stdout = _decode_output(exc.stdout, self.output_limit)
            stderr = _decode_output(exc.stderr, self.output_limit)
            status, exit_code = "cancelled", None
        except subprocess.TimeoutExpired as exc:
            stdout = _decode_output(exc.stdout, self.output_limit)
            stderr = _decode_output(exc.stderr, self.output_limit)
            status, exit_code = "timed_out", None
        except Exception as exc:
            stdout, stderr = "", "operation_failed:" + type(exc).__name__
            status, exit_code = "failed", None
        stdout, stderr = _bounded_text(stdout, self.output_limit), _bounded_text(stderr, self.output_limit)
        completed = _now()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            event_id = self._event(db, execution_id, status, {
                "command_sha256": payload.get("command_sha256", ""),
                "exit_code": exit_code, "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
                "stdout_bytes": len(stdout.encode()), "stderr_bytes": len(stderr.encode())})
            db.execute("""UPDATE command_executions SET execution_status=?,stdout=?,stderr=?,
                exit_code=?,completed_at=? WHERE execution_id=?""",
                (status, stdout, stderr, exit_code, completed, execution_id))
            self._purge_expired(db)
            db.commit()
        with self._condition:
            self._cancel_events.pop(execution_id, None)
            self._condition.notify_all()

    def cancel_by_idempotency(self, key: str, principal: str, operation: str) -> dict:
        with self._condition, closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM command_executions WHERE idempotency_key=?",
                             (key,)).fetchone()
            if row is None or row["caller_principal"] != principal or row["operation"] != operation:
                db.commit()
                return {"execution_status": "not_found"}
            if row["execution_status"] == "queued":
                self._pending.pop(row["execution_id"], None)
                self._event(db, row["execution_id"], "cancelled", {"phase": "queued"})
                db.execute("UPDATE command_executions SET execution_status='cancelled',cancel_requested=1,"
                           "completed_at=?,exit_code=NULL WHERE execution_id=?",
                           (_now(), row["execution_id"]))
            elif row["execution_status"] == "running":
                if not row["cancel_requested"]:
                    self._event(db, row["execution_id"], "cancellation_requested", {"phase": "running"})
                    db.execute("UPDATE command_executions SET cancel_requested=1 WHERE execution_id=?",
                               (row["execution_id"],))
                signal = self._cancel_events.get(row["execution_id"])
                if signal:
                    signal.set()
            db.commit()
            self._condition.notify_all()
        return self.get_by_idempotency(key, principal, operation)

    def get_by_idempotency(self, key: str, principal: str, operation: str) -> dict:
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM command_executions WHERE idempotency_key=?",
                             (key,)).fetchone()
            if row is None or row["caller_principal"] != principal or row["operation"] != operation:
                return {"execution_status": "not_found"}
            return _row_dict(row)

    def close(self):
        with self._condition:
            self._closing = True
            for signal in self._cancel_events.values():
                signal.set()
            self._condition.notify_all()
        self._worker.join(timeout=1)

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_dict(row) -> dict:
    if row is None:
        return {"execution_status": "not_found"}
    return {key: row[key] for key in row.keys()}


def _decode_output(value, limit):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value[:limit].decode("utf-8", "replace")
    return _bounded_text(str(value), limit)


def _validate_agent_request(request: dict) -> dict:
    expected = {"operation", "target_host", "privilege_level", "caller_principal",
                "caller_grant_id", "execution_grant_id", "reservation_id", "idempotency_key"}
    if not isinstance(request, dict) or set(request) != expected:
        task_expected = expected | {"host_id", "transport", "command"}
        if not isinstance(request, dict) or set(request) != task_expected:
            raise ValueError("agent_request_fields_invalid")
    if request["operation"] in {"command_task_standard", "command_task_elevated"}:
        if set(request) != expected | {"host_id", "transport", "command"}:
            raise ValueError("agent_request_fields_invalid")
        host_id = request["host_id"]
        if not isinstance(host_id, str) or host_id not in TASK_HOSTS:
            raise ValueError("command_host_not_registered")
        target, _scope, transport = TASK_HOSTS[host_id]
        privilege = request["operation"].removeprefix("command_task_")
        command = request["command"]
        if (request["target_host"] != target or request["transport"] != transport or
                request["privilege_level"] != privilege or privilege not in TASK_PRIVILEGES or
                not isinstance(command, str) or not command.strip() or
                len(command.encode("utf-8")) > MAX_COMMAND_CHARS or "\x00" in command):
            raise ValueError("agent_request_not_authorized_shape")
        request = dict(request)
        request["command_sha256"] = hashlib.sha256(command.encode("utf-8")).hexdigest()
        # The command is delivered to the runner but never written to the durable ledger.
    else:
        target, _scope, privilege = _safe_operation(request["operation"])
        if request["target_host"] != target or request["privilege_level"] != privilege:
            raise ValueError("agent_request_not_authorized_shape")
    if (not isinstance(request["caller_principal"], str) or
            not request["caller_principal"].startswith("steward:") or
            any(not isinstance(request[field], str) or not 1 <= len(request[field]) <= 256
                for field in ("caller_grant_id", "execution_grant_id", "reservation_id")) or
            not isinstance(request["idempotency_key"], str) or
            not re.fullmatch(r"cmd-[0-9a-f]{64}", request["idempotency_key"])):
        raise ValueError("agent_request_not_authorized_shape")
    return dict(request)


def _run_windows_operation(operation: str | dict, timeout: int):
    if operation == "powershell_identity":
        ps_script = ("$v = [ordered]@{ hostname = $env:COMPUTERNAME; "
                     "powershell_version = $PSVersionTable.PSVersion.ToString() }; "
                     "$v | ConvertTo-Json -Compress")
        argv = ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
                "-Command", ps_script]
    elif operation == "ssh_camrui_hostname":
        argv = ["ssh.exe", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "ClearAllForwardings=yes", "-o", "ForwardAgent=no",
                "-o", "RequestTTY=no", "-o", "HostKeyAlias=camrui",
                "192.168.1.155", "hostname"]
    elif isinstance(operation, dict) and operation.get("operation", "").startswith("command_task_"):
        transport = operation["transport"]
        command = operation["command"]
        privilege = operation["privilege_level"]
        if transport == "powershell":
            # The service account must be provisioned as a non-administrator.
            # A separate elevated caller/executor grant is necessary but cannot
            # by itself grant the Windows service OS privileges.
            if privilege == "elevated":
                raise PermissionError("windows_elevated_executor_not_configured")
            argv = ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
        elif transport == "ssh":
            # SSH aliases and strict known_hosts entries are administrator managed.
            # The standard SSH account must not have sudo rights; elevated requests
            # use non-interactive sudo and therefore fail closed if not granted.
            import shlex
            remote = (command if privilege == "standard" else
                      "sudo -n -- sh -lc " + shlex.quote(command))
            target, host_key_alias = SSH_HOST_TARGETS.get(
                operation["host_id"], (operation["host_id"], operation["host_id"]))
            argv = ["ssh.exe", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                    "-o", "ClearAllForwardings=yes", "-o", "ForwardAgent=no",
                    "-o", "RequestTTY=no", "-o", f"HostKeyAlias={host_key_alias}",
                    target, remote]
        else:
            raise ValueError("command_transport_not_supported")
    else:
        raise ValueError("command_operation_not_allowlisted")
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    out, err = bytearray(), bytearray()

    def drain(stream, destination):
        while True:
            chunk = stream.read(4096)
            if not chunk:
                return
            remaining = MAX_OUTPUT_BYTES - len(destination)
            if remaining > 0:
                destination.extend(chunk[:remaining])

    readers = [threading.Thread(target=drain, args=(process.stdout, out), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, err), daemon=True)]
    for reader in readers:
        reader.start()
    cancel_event = operation.get("_cancel_event") if isinstance(operation, dict) else None
    deadline = time.monotonic() + timeout
    try:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                process.kill()
                process.wait()
                for reader in readers:
                    reader.join(timeout=2)
                raise CommandCancelled(bytes(out), bytes(err))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            try:
                exit_code = process.wait(timeout=min(0.2, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        for reader in readers:
            reader.join(timeout=2)
        raise subprocess.TimeoutExpired(argv, timeout, output=bytes(out), stderr=bytes(err)) from None
    for reader in readers:
        reader.join(timeout=2)
    return (bytes(out).decode("utf-8", "replace"),
            bytes(err).decode("utf-8", "replace"), exit_code)


class _AgentHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def create_agent_handler(store: WindowsCommandAgentStore, bearer_token: str):
    if not isinstance(bearer_token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", bearer_token):
        raise ValueError("command_agent_token_invalid")

    class Handler(BaseHTTPRequestHandler):
        server_version = "RiverviewCommandAgent/1"

        def log_message(self, format, *args):
            return

        def _json(self, status, payload):
            body = _canonical_json(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            supplied = self.headers.get("Authorization", "")
            return hmac.compare_digest(supplied, "Bearer " + bearer_token)

        def do_POST(self):
            if self.path != "/v1/commands":
                self._json(404, {"error": "not_found"})
                return
            if not self._authorized():
                self._json(401, {"error": "not_authorized"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = MAX_BODY_BYTES + 1
            if not 0 < length <= MAX_BODY_BYTES:
                self._json(413, {"error": "request_too_large"})
                return
            try:
                request = json.loads(self.rfile.read(length))
                result = store.submit(request)
            except (ValueError, UnicodeError, json.JSONDecodeError):
                self._json(400, {"error": "invalid_command_request"})
                return
            except CommandAgentUnavailable:
                self._json(503, {"error": "command_queue_unavailable"})
                return
            self._json(201, result)

        def do_GET(self):
            if not self._authorized():
                self._json(401, {"error": "not_authorized"})
                return
            parsed = urlsplit(self.path)
            prefix = "/v1/commands/"
            if not parsed.path.startswith(prefix):
                self._json(404, {"error": "not_found"})
                return
            identifier = parsed.path[len(prefix):]
            if not identifier.startswith("by-key/"):
                self._json(404, {"error": "not_found"})
                return
            key = identifier[len("by-key/"):]
            query = parse_qs(parsed.query, max_num_fields=2)
            if set(query) != {"principal", "operation"} or any(len(v) != 1 for v in query.values()):
                self._json(400, {"error": "status_query_invalid"})
                return
            result = store.get_by_idempotency(key, query["principal"][0], query["operation"][0])
            self._json(200, result)

        def do_PUT(self):
            self._json(405, {"error": "method_not_allowed"})

        def do_DELETE(self):
            if not self._authorized():
                self._json(401, {"error": "not_authorized"})
                return
            parsed = urlsplit(self.path)
            prefix = "/v1/commands/by-key/"
            if not parsed.path.startswith(prefix):
                self._json(404, {"error": "not_found"})
                return
            query = parse_qs(parsed.query, max_num_fields=2)
            if set(query) != {"principal", "operation"} or any(len(v) != 1 for v in query.values()):
                self._json(400, {"error": "status_query_invalid"})
                return
            key = parsed.path[len(prefix):]
            result = store.cancel_by_idempotency(key, query["principal"][0],
                                                 query["operation"][0])
            self._json(200, result)

    return Handler


def serve_windows_agent(*, bind: str, port: int, store_path: str | Path,
                        token_file: str | Path, certificate_file: str | Path,
                        private_key_file: str | Path,
                        task_timeout_seconds=COMMAND_TASK_TIMEOUT_SECONDS,
                        retention_days=30):
    """Start the Windows-only HTTPS agent with OS-protected credentials."""
    import ipaddress
    address = ipaddress.ip_address(bind)
    if address.is_unspecified or address.is_loopback:
        raise ValueError("command_agent_bind_must_be_private_interface")
    token = Path(token_file).read_text(encoding="ascii").strip()
    store = WindowsCommandAgentStore(store_path, task_timeout_seconds=task_timeout_seconds,
                                     retention_days=retention_days)
    server = _AgentHTTPServer((str(address), int(port)), create_agent_handler(store, token))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(certificate_file), str(private_key_file))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        store.close()


def main():
    bind = os.environ.get("RIVERVIEW_COMMAND_AGENT_BIND", "")
    port = int(os.environ.get("RIVERVIEW_COMMAND_AGENT_PORT", "8443"))
    base = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Riverview" / "CommandGateway"
    serve_windows_agent(bind=bind, port=port,
        store_path=os.environ.get("RIVERVIEW_COMMAND_AGENT_DB", str(base / "executions.sqlite3")),
        token_file=os.environ.get("RIVERVIEW_COMMAND_AGENT_TOKEN_FILE", str(base / "agent.token")),
        certificate_file=os.environ.get("RIVERVIEW_COMMAND_AGENT_CERT_FILE", str(base / "agent.crt")),
        private_key_file=os.environ.get("RIVERVIEW_COMMAND_AGENT_KEY_FILE", str(base / "agent.key")),
        task_timeout_seconds=int(os.environ.get("RIVERVIEW_COMMAND_JOB_TIMEOUT_SECONDS",
                                               str(COMMAND_TASK_TIMEOUT_SECONDS))),
        retention_days=int(os.environ.get("RIVERVIEW_COMMAND_RETENTION_DAYS", "30")))

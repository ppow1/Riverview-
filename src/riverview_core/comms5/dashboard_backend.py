# Riverview Controlled Source
# File: src/riverview_core/comms5/dashboard_backend.py
# Component: COMMS5-CAMRUI-ADAPTER
# Revision: 1.0.9
# Purpose: Expose bounded current-runtime operations through Comms5
# Authority: Existing dashboard credential plus ingress-attested Steward principal
# Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Route proposal and complete bounded status operations through the fixed authenticated internal dashboard contract.
# Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Correlate authenticated transport probes to the dashboard request and surface truthful resource-policy status.
# Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Route durable work-order queue requests through the existing authenticated dashboard operation endpoint.
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Route stale-base recovery and durable worker policy operations through the existing authenticated operation endpoint.
# Changed: 2026-10-17 UTC | RV-COMMS5-PR100-CORRELATION-HEADER-20261017 | Keep ordinary status reads compatible with responses lacking optional request-correlation headers.
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Allow only the four review-exchange names through the existing attested Steward dashboard operation route.
# History: New file; no predecessor existed.
"""Narrow authenticated bridge to Riverview's existing dashboard API."""

from __future__ import annotations

import json
import os
import re
import stat
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
_READ_TOOLS = {
    "comms5_cme_status",
    "comms5_transport_probe",
}
_PROPOSAL_TOOLS = {
    "comms5_submit_steward_seed", "comms5_store_specification",
    "comms5_seed_status", "comms5_seed_lineage", "comms5_cancel_draft",
    "comms5_supersede_seed", "comms5_confirm_and_promote_seed",
}
_INTERNAL_TOOLS = _PROPOSAL_TOOLS | {
    "comms5_objective_status", "comms5_recent_steward_submissions",
    "comms5_resource_policy_status",
    "comms5_form_and_queue_work",
    "comms5_revalidate_and_queue_work",
    "comms5_set_resource_policy",
    "comms5_set_resource_policy_lock",
    "reasoning_exchange_list_requests", "reasoning_exchange_claim_request",
    "reasoning_exchange_submit_response", "reasoning_exchange_status",
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class DashboardBackendUnavailable(RuntimeError):
    """The authenticated dashboard projection could not provide a valid result."""


class DashboardRecordNotFound(RuntimeError):
    """The current authoritative projection has no record for the requested ID."""


class DashboardOperationConflict(RuntimeError):
    """A valid operation conflicts with the current durable lifecycle state."""


class DashboardReadBackend:
    """Call only fixed read endpoints on the loopback dashboard.

    The dashboard bearer is supplied as a systemd credential. This adapter does
    not accept caller-provided URLs, paths, headers, or credentials and never
    calls dashboard mutation endpoints.
    """

    IMPLEMENTATION_STATUS = {
        "comms5_objective_status": "IMPLEMENTED",
        "comms5_cme_status": "IMPLEMENTED",
        "comms5_recent_steward_submissions": "IMPLEMENTED",
        "comms5_transport_probe": "IMPLEMENTED",
        "comms5_resource_policy_status": "IMPLEMENTED",
        "comms5_form_and_queue_work": "IMPLEMENTED",
        "comms5_submit_steward_seed": "IMPLEMENTED",
        "comms5_store_specification": "IMPLEMENTED",
        "comms5_seed_status": "IMPLEMENTED",
        "comms5_seed_lineage": "IMPLEMENTED",
        "comms5_cancel_draft": "IMPLEMENTED",
        "comms5_supersede_seed": "IMPLEMENTED",
        "comms5_confirm_and_promote_seed": "IMPLEMENTED",
        "comms5_revalidate_and_queue_work": "IMPLEMENTED",
        "comms5_set_resource_policy": "IMPLEMENTED",
        "comms5_set_resource_policy_lock": "IMPLEMENTED",
        "reasoning_exchange_list_requests": "IMPLEMENTED",
        "reasoning_exchange_claim_request": "IMPLEMENTED",
        "reasoning_exchange_submit_response": "IMPLEMENTED",
        "reasoning_exchange_status": "IMPLEMENTED",
    }

    def __init__(self, *, base_url=None, credential_file=None, timeout=3.0):
        base_url = base_url or os.environ.get(
            "RIVERVIEW_COMMS5_DASHBOARD_URL", "http://127.0.0.1:8767"
        )
        parsed = urlsplit(base_url)
        try:
            port = parsed.port
        except ValueError:
            port = None
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"}
                or port is None or not 8700 <= port <= 8799
                or parsed.username or parsed.password or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment):
            raise ValueError("dashboard_backend_must_use_configured_loopback")
        if not 0.1 <= float(timeout) <= 5.0:
            raise ValueError("dashboard_backend_timeout_out_of_range")
        if credential_file is None:
            credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
            credential_file = (Path(credential_dir) / "dashboard-token"
                               if credential_dir else Path(""))
        token_path = Path(credential_file)
        try:
            if token_path.is_symlink():
                raise OSError("credential_symlink")
            descriptor = os.open(token_path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                                 | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(descriptor, "r", encoding="ascii") as stream:
                metadata = os.fstat(stream.fileno())
                if not stat.S_ISREG(metadata.st_mode):
                    raise OSError("credential_not_regular")
                mode = metadata.st_mode & 0o777
                credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
                systemd_credential = (credential_dir is not None
                    and token_path.parent.resolve() == Path(credential_dir).resolve()
                    and token_path.name == "dashboard-token")
                if (mode not in {0o400, 0o440} if systemd_credential
                        else bool(mode & 0o077)):
                    raise OSError("credential_permissions_invalid")
                token = stream.read().strip()
        except (OSError, UnicodeError):
            raise DashboardBackendUnavailable("dashboard_credential_unavailable") from None
        if not _TOKEN.fullmatch(token):
            raise DashboardBackendUnavailable("dashboard_credential_invalid")
        self._base_url = f"{parsed.scheme}://{parsed.netloc}"
        self._token = token
        self.timeout = float(timeout)
        self._opener = build_opener(_NoRedirect())

    def _open(self, request):
        return self._opener.open(request, timeout=self.timeout)

    def _post_operation(self, tool, arguments):
        request = Request(self._base_url + "/api/v1/internal/comms5/operation",
            data=json.dumps({"tool": tool, "arguments": arguments},
                separators=(",", ":"), allow_nan=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + self._token,
                     "Content-Type": "application/json",
                     "Accept": "application/json",
                     "X-Riverview-Comms5": "1",
                     "X-Riverview-Comms5-Principal": "steward"}, method="POST")
        try:
            with self._open(request) as response:
                if response.status != 200 or response.headers.get_content_type() != "application/json":
                    raise DashboardBackendUnavailable("dashboard_operation_http_status")
                payload = response.read(1_048_577)
        except HTTPError as exc:
            try:
                error = json.loads(exc.read(4096))
            except Exception:
                error = {}
            code = error.get("error") if isinstance(error, dict) else None
            if code == "proposal_not_found":
                raise DashboardRecordNotFound("proposal_not_found") from None
            if code == "objective_not_found":
                raise DashboardRecordNotFound("objective_not_found") from None
            if code in {"comms5_operation_not_authorized", "comms5_transport_attestation_required"}:
                raise PermissionError("comms5_operation_not_authorized") from None
            if code == "proposal_lifecycle_conflict":
                raise DashboardOperationConflict("proposal_lifecycle_conflict") from None
            if code == "invalid_comms5_operation":
                raise ValueError("invalid_comms5_operation") from None
            raise DashboardBackendUnavailable("dashboard_operation_http_status") from None
        except (URLError, TimeoutError, OSError):
            raise DashboardBackendUnavailable("dashboard_operation_unavailable") from None
        if len(payload) > 1_048_576:
            raise DashboardBackendUnavailable("dashboard_response_exceeds_limit")
        try:
            value = json.loads(payload)
        except (UnicodeError, json.JSONDecodeError):
            raise DashboardBackendUnavailable("dashboard_operation_response_invalid") from None
        if not isinstance(value, dict):
            raise DashboardBackendUnavailable("dashboard_operation_response_invalid")
        return value

    @property
    def supported_tools(self):
        return frozenset(_READ_TOOLS | _INTERNAL_TOOLS)

    def call_authenticated(self, name, arguments, *, principal=None):
        if name == "comms5_transport_probe" and principal != "steward":
            raise PermissionError("authenticated Steward ingress required")
        if name in _INTERNAL_TOOLS:
            if principal != "steward":
                raise PermissionError("authenticated Steward ingress required")
            return self._post_operation(name, arguments)
        return self.call(name, arguments)

    def _get(self, path):
        return self._get_response(path)[0]

    def _get_response(self, path):
        if path not in {"/api/v1/status", "/api/v1/attention"}:
            raise DashboardBackendUnavailable("dashboard_path_not_allowlisted")
        request = Request(self._base_url + path, headers={
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
        })
        try:
            with self._open(request) as response:
                if response.status != 200:
                    raise DashboardBackendUnavailable("dashboard_http_status")
                if response.headers.get_content_type() != "application/json":
                    raise DashboardBackendUnavailable("dashboard_content_type_invalid")
                payload = response.read(1_048_577)
                request_id = (response.headers.get("X-Request-ID")
                              if callable(getattr(response.headers, "get", None)) else None)
        except HTTPError as exc:
            raise DashboardBackendUnavailable("dashboard_http_status") from None
        except (URLError, TimeoutError, OSError):
            raise DashboardBackendUnavailable("dashboard_unavailable") from None
        if len(payload) > 1_048_576:
            raise DashboardBackendUnavailable("dashboard_response_exceeds_limit")
        try:
            value = json.loads(payload)
        except (UnicodeError, json.JSONDecodeError):
            raise DashboardBackendUnavailable("dashboard_response_invalid") from None
        if not isinstance(value, dict):
            raise DashboardBackendUnavailable("dashboard_response_invalid")
        return value, request_id

    def call(self, name, arguments):
        if name not in _READ_TOOLS:
            raise ValueError("dashboard_tool_not_supported")
        if name == "comms5_transport_probe":
            probe_id = arguments.get("probe_id")
            if (not isinstance(probe_id, str) or not 1 <= len(probe_id) <= 128
                    or not re.fullmatch(r"[A-Za-z0-9._:-]+", probe_id)):
                raise ValueError("invalid_probe_id")
            started = time.perf_counter()
            value, dashboard_request_id = self._get_response("/api/v1/status")
            if (not isinstance(dashboard_request_id, str) or
                    not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", dashboard_request_id)):
                raise DashboardBackendUnavailable("dashboard_request_correlation_missing")
            elapsed = max(0.0, (time.perf_counter() - started) * 1000)
            return {"status": "available", "executed": True,
                    "implementation_status": "IMPLEMENTED",
                    "probe_id": probe_id, "correlation_id": probe_id,
                    "dashboard_request_id": dashboard_request_id,
                    "observed_at": value.get("observed_at"),
                    "dashboard_projection_status": value.get("projection_status"),
                    "dashboard_round_trip_ms": round(elapsed, 3),
                    "verified_path": ["authenticated_comms5_request",
                                      "camrui_comms5_adapter",
                                      "dashboard_loopback_read_api"]}
        if name == "comms5_cme_status":
            value = self._get("/api/v1/status")
            cme = value.get("cme")
            if not isinstance(cme, dict):
                raise DashboardBackendUnavailable("cme_projection_missing")
            return {"status": "available" if value.get("projection_status") == "healthy"
                    else value.get("projection_status", "unknown"),
                    "source": "riverview_dashboard_status_projection",
                    "cme": cme,
                    "observed_at": value.get("observed_at")}

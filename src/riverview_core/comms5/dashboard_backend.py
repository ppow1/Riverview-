# Riverview Controlled Source
# File: src/riverview_core/comms5/dashboard_backend.py
# Component: COMMS5-CAMRUI-ADAPTER
# Revision: 1.0.0
# Purpose: Expose bounded read-only dashboard projections through Comms5
# Authority: Existing authenticated dashboard credential; fixed loopback read routes only
# History: New file; no predecessor existed.
"""Narrow read-only bridge to Riverview's existing authenticated dashboard API."""

from __future__ import annotations

import json
import os
import re
import stat
import time
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
_OBJECTIVE_ID = re.compile(r"^objective:[A-Za-z0-9._:-]{1,120}$")
_READ_TOOLS = {
    "comms5_objective_status",
    "comms5_cme_status",
    "comms5_recent_steward_submissions",
    "comms5_transport_probe",
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class DashboardBackendUnavailable(RuntimeError):
    """The authenticated dashboard projection could not provide a valid result."""


class DashboardRecordNotFound(RuntimeError):
    """The current authoritative projection has no record for the requested ID."""


class DashboardReadBackend:
    """Call only fixed read endpoints on the loopback dashboard.

    The dashboard bearer is supplied as a systemd credential. This adapter does
    not accept caller-provided URLs, paths, headers, or credentials and never
    calls dashboard mutation endpoints.
    """

    IMPLEMENTATION_STATUS = {
        "comms5_objective_status": "PARTIALLY_IMPLEMENTED",
        "comms5_cme_status": "IMPLEMENTED",
        "comms5_recent_steward_submissions": "PARTIALLY_IMPLEMENTED",
        "comms5_transport_probe": "PARTIALLY_IMPLEMENTED",
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

    @property
    def supported_tools(self):
        return frozenset(_READ_TOOLS)

    def _get(self, path):
        objective_detail = re.fullmatch(r"/api/v1/objectives/(objective:[A-Za-z0-9._:-]{1,120})", path)
        objective_list = re.fullmatch(r"/api/v1/objectives\?limit=[1-9][0-9]{0,2}", path)
        if (path not in {"/api/v1/status", "/api/v1/attention"}
                and objective_list is None and objective_detail is None):
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
        except HTTPError as exc:
            if exc.code == 404 and objective_detail is not None:
                raise DashboardRecordNotFound("objective_not_found") from None
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
        return value

    @staticmethod
    def _safe_objective(item):
        # Deliberately omit request, acceptance text, scope, and submitter fields.
        allowed = (
            "objective_id", "status", "assignment_id", "assignment_state",
            "attempt_id", "artifact", "verification", "dispatch_failures",
            "last_dispatch_failure_at", "verification_failures",
            "last_verification_failure_at", "source_revision", "source_sha256",
            "revision", "created_at", "updated_at",
        )
        result = {key: item[key] for key in allowed if key in item}
        result["available_detail"] = [
            "objective_state", "linked_assignment", "latest_attempt",
            "artifact_metadata", "latest_verification", "failure_counts",
        ]
        result["unavailable_detail"] = [
            "stage_lineage", "authority_record", "execution_intent",
        ]
        return result

    def call(self, name, arguments):
        if name not in _READ_TOOLS:
            raise ValueError("dashboard_tool_not_supported")
        if name == "comms5_transport_probe":
            probe_id = arguments.get("probe_id")
            if (not isinstance(probe_id, str) or not 1 <= len(probe_id) <= 128
                    or not re.fullmatch(r"[A-Za-z0-9._:-]+", probe_id)):
                raise ValueError("invalid_probe_id")
            started = time.perf_counter()
            value = self._get("/api/v1/status")
            elapsed = max(0.0, (time.perf_counter() - started) * 1000)
            return {"status": "available", "executed": True,
                    "implementation_status": "PARTIALLY_IMPLEMENTED",
                    "probe_id": probe_id, "correlation_id": str(uuid4()),
                    "observed_at": value.get("observed_at"),
                    "dashboard_projection_status": value.get("projection_status"),
                    "dashboard_round_trip_ms": round(elapsed, 3),
                    "verified_path": ["comms5_adapter", "dashboard_loopback_read_api"],
                    "unverified_path": ["external_client_to_ionoge", "ionoge_tunnel_to_camrui"]}
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

        if name == "comms5_objective_status":
            objective_id = arguments.get("objective_id")
            if not isinstance(objective_id, str) or not _OBJECTIVE_ID.fullmatch(objective_id):
                raise ValueError("invalid_objective_id")
            try:
                item = self._get("/api/v1/objectives/" + quote(objective_id, safe=":._-"))
            except DashboardRecordNotFound:
                return {"status": "not_found", "objective_id": objective_id,
                        "executed": True, "implementation_status": "PARTIALLY_IMPLEMENTED"}
            if item.get("objective_id") != objective_id:
                raise DashboardBackendUnavailable("objective_projection_mismatch")
            return {"status": "available", "executed": True,
                    "implementation_status": "PARTIALLY_IMPLEMENTED",
                    "objective": self._safe_objective(item)}

        limit = arguments.get("limit", 20)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid_limit")
        value = self._get("/api/v1/objectives?" + urlencode({"limit": str(limit)}))
        items = value.get("items")
        if value.get("status") != "available" or not isinstance(items, list):
            raise DashboardBackendUnavailable("objective_projection_unavailable")
        submissions = []
        for item in items:
            if not isinstance(item, dict):
                raise DashboardBackendUnavailable("objective_projection_invalid")
            submitter = item.get("submitter_id")
            if isinstance(submitter, str) and submitter.startswith("steward:"):
                submissions.append({key: item[key] for key in (
                    "objective_id", "status", "assignment_id", "assignment_state",
                    "created_at", "updated_at") if key in item})
        return {"status": "available", "executed": True,
                "implementation_status": "PARTIALLY_IMPLEMENTED",
                "source": "steward_submitted_objective_projection",
                "ordering": "dashboard_updated_at_descending",
                "items": submissions, "limit": limit,
                "truncated": bool(value.get("truncated"))}

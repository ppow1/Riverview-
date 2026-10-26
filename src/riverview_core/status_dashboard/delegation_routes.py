# Riverview~ Controlled Source
# File: src/riverview_core/status_dashboard/delegation_routes.py
# Component: STEWARD-DELEGATION-APPROVAL-API
# Revision: 1.0.0
# Purpose: Route authenticated Steward list, detail, grant inspection and revocation requests
# Execution Model: Same-origin request-driven API
# Observability: Structured safe status/error codes; no credentials in responses
# Dependencies: Existing account-session/CSRF validation and protected delegation adapter
# Authority: Steward role, steward:camrui binding, and authority.grant institution scope
# Changed: 2026-10-26 UTC | RV-V2-DELEGATION-PROJECTION-001 | Expose bounded reads and canonical grant revocation.
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# Tests: tests/test_delegation_routes.py
# History: Initial controlled source
"""Narrow HTTP adapter for the existing Steward delegation authority."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

from .delegation_projection import get_request, list_grants, list_requests, revoke_grant


_REQUEST = re.compile(r"^/api/v1/steward/delegation-grant-requests/(delegation-request:[A-Za-z0-9._:-]{1,128})$")
_REVOKE = re.compile(r"^/api/v1/steward/delegated-grants/(grant:[A-Za-z0-9._:-]{1,128})/revoke$")
_REQUESTS = "/api/v1/steward/delegation-grant-requests"
_GRANTS = "/api/v1/steward/delegated-grants"
_OPTIONS = _REQUESTS + "/options"


def is_route(method: str, path: str) -> bool:
    return ((method in {"GET", "HEAD"} and
             (path in {_REQUESTS, _GRANTS, _OPTIONS} or _REQUEST.fullmatch(path) is not None)) or
            (method == "POST" and (path == _REQUESTS or _REVOKE.fullmatch(path) is not None)))


def _request_context(handler):
    identity = getattr(handler, "_account_identity", None)
    if (not getattr(handler, "_account_cookie_authenticated", False) or not identity or
            "steward" not in identity.get("roles", ()) or
            identity.get("authority_principal_id") != "steward:camrui"):
        raise PermissionError("authenticated_steward_required")
    registry = getattr(handler.server, "_authority_registry", None)
    if registry is None:
        raise RuntimeError("delegation_authority_unavailable")
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
    token_path = Path(credential_dir) / "authority-steward-token" if credential_dir else None
    if registry is None or token_path is None or token_path.is_symlink() or not token_path.is_file():
        raise RuntimeError("delegation_authority_unavailable")
    if token_path.resolve().parent != Path(credential_dir).resolve():
        raise RuntimeError("delegation_authority_unavailable")
    token = token_path.read_text(encoding="ascii").strip()
    try:
        actor = registry.authorize(token, "authority.grant", "institution")
    except Exception as exc:
        from riverview_core.institutional_authority.registry import AuthorityDenied
        if isinstance(exc, AuthorityDenied):
            raise PermissionError("steward_authority_denied") from None
        raise RuntimeError("delegation_authority_unavailable") from None
    if actor.get("principal_id") != "steward:camrui" or actor.get("principal_kind") != "steward":
        raise PermissionError("steward_authority_denied")
    return identity["authority_principal_id"], registry


def _registered_control_capabilities(handler, principal_id):
    store = getattr(handler.server, "_permission_store", None)
    if store is None or not callable(getattr(store,"list_profiles",None)):
        raise RuntimeError("capability_registry_unavailable")
    result=store.list_profiles(principal_id)
    entries=result.get("capabilities") if isinstance(result,dict) else None
    if not isinstance(entries,list):
        raise RuntimeError("capability_registry_unavailable")
    allowed={}
    for item in entries:
        if not isinstance(item,dict) or item.get("enabled") is not True or item.get("registration_blocker"):
            continue
        capability_id=item.get("capability_id")
        action=item.get("authority_action")
        if (isinstance(capability_id,str) and capability_id==action and
                re.fullmatch(r"hardware\.gpu\.workload\.(?:read|start|stop|switch)",action or "")):
            allowed[capability_id]={"capability_id":capability_id,"action":action,
                "description":item.get("description") or capability_id}
    return allowed


def _request_options(handler, principal_id):
    telemetry = getattr(handler.server, "_resource_telemetry", None)
    if telemetry is None or not callable(getattr(telemetry, "read", None)):
        raise RuntimeError("hardware_host_registry_unavailable")
    snapshot = telemetry.read()
    registrations = telemetry.workload_controller_registrations()
    canonical = _registered_control_capabilities(handler,principal_id)
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("hosts"), list):
        raise RuntimeError("hardware_host_registry_unavailable")
    hosts = []
    for host in snapshot["hosts"]:
        if not isinstance(host, dict) or host.get("identity_state") != "verified":
            continue
        host_id = host.get("host_id")
        registration = registrations.get(host_id)
        if not isinstance(registration, dict):
            continue
        services = registration.get("services", [])
        if not isinstance(services, list) or not services:
            continue
        hosts.append({"host_id": host_id, "display_name": host.get("display_name"),
                      "scope_ref": f"host:{host_id}",
                      "capabilities": [canonical[item.get("capability_id")]
                                       for item in registration.get("capabilities", [])
                                       if isinstance(item,dict) and item.get("capability_id") in canonical],
                      "services": [{"service_id": item["service_id"],
                                    "display_name": item["display_name"]}
                                   for item in services if isinstance(item, dict)]})
    return {"status": "available", "hosts": hosts,
            "expires_in_days": [1, 7, 30],
            "requester_principal_id": principal_id,
            "target_principal_id": principal_id}


def _create_request(handler):
    principal_id, registry = _request_context(handler)
    data = handler._json_body(4096)
    required = {"host_id", "action", "purpose", "valid_until", "idempotency_key"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("delegation_request_fields_invalid")
    host_id, action = data["host_id"], data["action"]
    if (not isinstance(host_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", host_id) or
            action not in {f"hardware.gpu.workload.{value}" for value in ("read", "start", "stop", "switch")}):
        raise ValueError("delegation_request_capability_invalid")
    if (not isinstance(data["purpose"], str) or not 8 <= len(data["purpose"].strip()) <= 500):
        raise ValueError("delegation_request_purpose_invalid")
    idempotency_key = data["idempotency_key"]
    if not isinstance(idempotency_key, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{16,200}", idempotency_key):
        raise ValueError("delegation_request_idempotency_invalid")
    try:
        valid_until = datetime.fromisoformat(data["valid_until"].replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise ValueError("delegation_request_expiry_invalid") from None
    if valid_until.tzinfo is None or not datetime.now(timezone.utc) < valid_until <= datetime.now(timezone.utc) + timedelta(days=30):
        raise ValueError("delegation_request_expiry_invalid")
    telemetry = getattr(handler.server, "_resource_telemetry", None)
    if telemetry is None:
        raise RuntimeError("hardware_host_registry_unavailable")
    snapshot = telemetry.read()
    registrations = telemetry.workload_controller_registrations()
    host = next((item for item in snapshot.get("hosts", [])
                 if isinstance(item, dict) and item.get("host_id") == host_id), None)
    registration = registrations.get(host_id)
    canonical = _registered_control_capabilities(handler,principal_id)
    allowed = {item.get("action") for item in registration.get("capabilities", [])
               if isinstance(item, dict) and item.get("capability_id") in canonical} if isinstance(registration, dict) else set()
    if (host is None or host.get("identity_state") != "verified" or not registration or
            action not in allowed):
        raise ValueError("delegation_request_target_unavailable")
    return registry.request_grant(requester_id=principal_id, principal_id=principal_id,
        action=action, scope_ref=f"host:{host_id}", policy_ref="policy:delegation.v1",
        request_ref=data["purpose"].strip(), max_uses=None, valid_until=valid_until,
        idempotency_key=idempotency_key)


def _one(query, key, default):
    values = query.get(key)
    if values is None:
        return default
    if len(values) != 1:
        raise ValueError("query_parameter_repeated")
    return values[0]


def dispatch(handler, parsed, request_id):
    """Send one matched delegation request; caller has already validated session and CSRF."""
    if not is_route(handler.command, parsed.path):
        return False
    identity = getattr(handler, "_account_identity", None)
    if (not getattr(handler, "_account_cookie_authenticated", False) or not identity or
            "steward" not in identity.get("roles", ()) or
            identity.get("authority_principal_id") != "steward:camrui"):
        handler._error(403, "authenticated_steward_required", request_id)
        return True
    if handler.command in {"GET", "HEAD"} and parsed.path == _OPTIONS:
        try:
            principal_id,_ = _request_context(handler)
            handler._json(200, _request_options(handler,principal_id), request_id)
        except PermissionError:
            handler._error(403, "steward_authority_denied", request_id)
        except Exception as exc:
            handler._error(503, str(exc) if str(exc).startswith(("delegation_", "hardware_"))
                           else "hardware_host_registry_unavailable", request_id)
        return True
    if handler.command == "POST" and parsed.path == _REQUESTS:
        try:
            result = _create_request(handler)
            handler._json(201, result, request_id)
        except PermissionError:
            handler._error(403, "steward_authority_denied", request_id)
        except (ValueError, TypeError, json.JSONDecodeError):
            handler._error(400, "invalid_delegation_request", request_id)
        except Exception as exc:
            from riverview_core.institutional_authority.registry import (
                AuthorityDenied, IdentityConflict, RegistryUnavailable)
            if isinstance(exc, AuthorityDenied):
                handler._error(403, "steward_authority_denied", request_id)
            elif isinstance(exc, IdentityConflict):
                handler._error(409, "delegation_state_conflict", request_id)
            elif isinstance(exc, RegistryUnavailable):
                handler._error(503, "delegation_authority_unavailable", request_id)
            else:
                handler._error(503, "delegation_request_unavailable", request_id)
        return True
    operations = getattr(handler.server, "_comms5_operations", None)
    adapter = getattr(operations, "delegation_grant_requests", None) if operations else None
    if adapter is None:
        handler._error(503, "delegation_authority_unavailable", request_id)
        return True
    try:
        if handler.command in {"GET", "HEAD"}:
            query = parse_qs(parsed.query, keep_blank_values=False, max_num_fields=4)
            if parsed.path == _REQUESTS:
                if set(query) - {"status", "limit"}:
                    raise ValueError("invalid_query")
                result = list_requests(adapter, status=_one(query, "status", "pending"),
                                       limit=int(_one(query, "limit", "50")))
            elif parsed.path == _GRANTS:
                if set(query) - {"state", "limit"}:
                    raise ValueError("invalid_query")
                result = list_grants(adapter, state=_one(query, "state", "active"),
                                     limit=int(_one(query, "limit", "50")))
            else:
                if query:
                    raise ValueError("invalid_query")
                result = get_request(adapter, _REQUEST.fullmatch(parsed.path).group(1))
            handler._json(200, result, request_id)
            return True
        data = handler._json_body(8 * 1024)
        if set(data) - {"confirm", "reason_code"} or data.get("confirm") is not True:
            raise ValueError("explicit_confirmation_required")
        result = revoke_grant(adapter, _REVOKE.fullmatch(parsed.path).group(1),
                              confirm=data["confirm"],
                              reason_code=data.get("reason_code", "steward_revoked"))
        handler._json(200, {"status": "revoked", "grant_id": _REVOKE.fullmatch(parsed.path).group(1),
                            "authority_result": result}, request_id)
        return True
    except OverflowError:
        handler._error(413, "request_too_large", request_id)
    except (ValueError, TypeError, json.JSONDecodeError):
        handler._error(400, "invalid_delegation_request", request_id)
    except PermissionError:
        handler._error(403, "steward_authority_denied", request_id)
    except RuntimeError as exc:
        code = str(exc) if str(exc).startswith(("delegation_", "hardware_")) else "delegation_authority_unavailable"
        handler._error(503, code, request_id)
    except Exception as exc:
        from riverview_core.institutional_authority.registry import (
            AuthorityDenied, IdentityConflict, RegistryUnavailable)
        if isinstance(exc, AuthorityDenied):
            handler._error(403, "steward_authority_denied", request_id)
        elif isinstance(exc, IdentityConflict):
            handler._error(409, "delegation_state_conflict", request_id)
        elif isinstance(exc, RegistryUnavailable):
            handler._error(503, "delegation_authority_unavailable", request_id)
        else:
            handler._error(503, "delegation_projection_unavailable", request_id)
    return True

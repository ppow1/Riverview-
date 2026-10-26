# Riverview~ Controlled Source
# File: src/riverview_core/status_dashboard/delegation_routes.py
# Component: STEWARD-DELEGATION-APPROVAL-API
# Revision: 1.0.1
# Purpose: Route authenticated Steward list, detail, grant inspection and revocation requests
# Execution Model: Same-origin request-driven API
# Observability: Structured safe status/error codes; no credentials in responses
# Dependencies: Existing account-session/CSRF validation and protected delegation adapter
# Authority: Steward role, steward:camrui binding, and authority.grant institution scope
# Changed: 2026-10-26 UTC | RV-V2-DELEGATION-PROJECTION-001 | Expose bounded reads and canonical grant revocation.
# Changed: 2026-10-26 UTC | RV-PR342-FINITE-USE-WITHOUT-EXPIRY | Permit a finite-use-only GPU delegation request through the canonical bounded-grant policy.
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# Tests: tests/test_delegation_routes.py
# History: Initial controlled source
"""Narrow HTTP adapter for the existing Steward delegation authority."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

from riverview_core.comms5.delegation_policy import (
    DELEGATED_ACTION, DELEGATED_POLICY, DELEGATED_PROJECT_SCOPE,
)

from .delegation_projection import get_request, list_grants, list_requests, revoke_grant


_REQUEST = re.compile(r"^/api/v1/steward/delegation-grant-requests/(delegation-request:[A-Za-z0-9._:-]{1,128})$")
_DECISION = re.compile(r"^/api/v1/steward/delegation-grant-requests/(delegation-request:[A-Za-z0-9._:-]{1,128})/decision$")
_REVOKE = re.compile(r"^/api/v1/steward/delegated-grants/(grant:[A-Za-z0-9._:-]{1,128})/revoke$")
_REQUESTS = "/api/v1/steward/delegation-grant-requests"
_GRANTS = "/api/v1/steward/delegated-grants"
_OPTIONS = _REQUESTS + "/options"


def is_route(method: str, path: str) -> bool:
    return ((method in {"GET", "HEAD"} and
             (path in {_REQUESTS, _GRANTS, _OPTIONS} or _REQUEST.fullmatch(path) is not None)) or
            (method == "POST" and (path == _REQUESTS or _DECISION.fullmatch(path) is not None or
                                    _REVOKE.fullmatch(path) is not None)))


def _request_context(handler):
    identity = getattr(handler, "_account_identity", None)
    if (not getattr(handler, "_account_cookie_authenticated", False) or not identity or
            "steward" not in identity.get("roles", ()) or
            identity.get("authority_principal_id") != "steward:camrui"):
        raise PermissionError("authenticated_steward_required")
    operations = getattr(handler.server, "_comms5_operations", None)
    adapter = getattr(operations, "delegation_grant_requests", None) if operations else None
    if adapter is None or not callable(getattr(adapter, "_authenticated_steward", None)):
        raise RuntimeError("delegation_authority_unavailable")
    registry = getattr(adapter, "_registry", None)
    token = getattr(adapter, "_steward_token", None)
    if registry is None or not isinstance(token, str) or len(token) < 32:
        raise RuntimeError("delegation_authority_unavailable")
    try:
        principal_id = adapter._authenticated_steward()
        actor = registry.authorize(token, "authority.grant", "institution")
    except Exception as exc:
        from riverview_core.institutional_authority.registry import AuthorityDenied
        if isinstance(exc, AuthorityDenied):
            raise PermissionError("steward_authority_denied") from None
        raise RuntimeError("delegation_authority_unavailable") from None
    if (principal_id != "steward:camrui" or actor.get("principal_id") != principal_id or
            actor.get("principal_kind") != "steward"):
        raise PermissionError("steward_authority_denied")
    return principal_id, registry


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
    operations = getattr(handler.server, "_comms5_operations", None)
    adapter = getattr(operations, "delegation_grant_requests", None) if operations else None
    codex_target = "service:chatgpt"  # principal emitted by the existing Comms5 OAuth boundary
    executor_registered = bool(operations and
        "comms5_submit_direct_engineering_task" in getattr(operations, "SUPPORTED", ()))
    target_registered = bool(adapter and callable(getattr(adapter, "registered_target", None))
                             and adapter.registered_target(codex_target, principal_kind="service"))
    codex_available = executor_registered and target_registered
    codex_unavailable_reason = (None if codex_available else
        "codex_task_operation_not_registered" if not executor_registered else
        "target_principal_not_registered_active")
    return {"status": "available", "hosts": hosts,
            "authorization_types": [{
                "type_id": "gpu_host", "label": "Registered GPU host operation",
                "scope_kind": "host", "target_principal_id": principal_id,
                "max_expiry_days": 365, "max_uses": 1000000,
                "usage_limits_supported": True, "combined_limits_supported": True,
                "non_expiring_supported": True,
                "non_expiring_requires_usage_limit": True,
            }, {
                "type_id": "comms5_codex", "label": "ChatGPT via Comms5 to existing Codex task submission",
                "scope_kind": "project", "scope_ref": DELEGATED_PROJECT_SCOPE,
                "target_principal_id": codex_target,
                "action": DELEGATED_ACTION,
                "policy_ref": DELEGATED_POLICY,
                "status": "available" if codex_available else "unavailable",
                "unavailable_reason": codex_unavailable_reason,
                "max_expiry_days": 1, "effective_expiry_hours_after_approval": 24,
                "usage_limits_supported": False, "combined_limits_supported": False,
                "non_expiring_supported": False,
                "additional_authority_required": ["objective.submit", "assignment.create", "assignment.execute", "assignment.verify"],
            }],
            "expires_in_days": [1, 7, 30, 90, 180, 365],
            "requester_principal_id": principal_id,
            "target_principal_id": principal_id}


def _create_request(handler):
    principal_id, registry = _request_context(handler)
    data = handler._json_body(4096)
    required = {"authorization_type_id", "action", "purpose", "valid_until", "max_uses", "idempotency_key"}
    if (not isinstance(data, dict) or
            (set(data) != required | {"host_id"} and set(data) != required)):
        raise ValueError("delegation_request_fields_invalid")
    kind, host_id, action = data["authorization_type_id"], data.get("host_id"), data["action"]
    max_uses = data["max_uses"]
    if max_uses is not None and (type(max_uses) is not int or not 1 <= max_uses <= 1_000_000):
        raise ValueError("delegation_request_usage_limit_invalid")
    if (not isinstance(data["purpose"], str) or not 8 <= len(data["purpose"].strip()) <= 500):
        raise ValueError("delegation_request_purpose_invalid")
    idempotency_key = data["idempotency_key"]
    if not isinstance(idempotency_key, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{16,200}", idempotency_key):
        raise ValueError("delegation_request_idempotency_invalid")
    try:
        valid_until = (datetime.fromisoformat(data["valid_until"].replace("Z", "+00:00"))
                       if data["valid_until"] is not None else None)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("delegation_request_expiry_invalid") from None
    if valid_until is not None and (valid_until.tzinfo is None or not datetime.now(timezone.utc) < valid_until <= datetime.now(timezone.utc) + timedelta(days=365)):
        raise ValueError("delegation_request_expiry_invalid")
    if kind == "gpu_host":
        if (not isinstance(host_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", host_id) or
                action not in {f"hardware.gpu.workload.{value}" for value in ("read", "start", "stop", "switch")}):
            raise ValueError("delegation_request_capability_invalid")
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
                   if isinstance(item,dict) and item.get("capability_id") in canonical} if isinstance(registration,dict) else set()
        if (host is None or host.get("identity_state") != "verified" or not registration or action not in allowed):
            raise ValueError("delegation_request_target_unavailable")
        if valid_until is None and max_uses is None:
            raise ValueError("delegation_request_requires_use_limit_or_expiry")
        scope_ref, target = f"host:{host_id}", principal_id
        return registry.request_grant(requester_id=principal_id, principal_id=target,
            action=action, scope_ref=scope_ref, policy_ref="policy:delegation.v1",
            request_ref=data["purpose"].strip(), max_uses=max_uses, valid_until=valid_until,
            idempotency_key=idempotency_key)
    if kind == "comms5_codex":
        if (host_id is not None or action != DELEGATED_ACTION or max_uses is not None
                or valid_until is None):
            raise ValueError("delegation_request_policy_not_supported")
        if valid_until > datetime.now(timezone.utc) + timedelta(days=1):
            raise ValueError("delegation_request_policy_maximum_expiry_24h")
        operations = getattr(handler.server, "_comms5_operations", None)
        adapter = getattr(operations, "delegation_grant_requests", None) if operations else None
        if (not operations or "comms5_submit_direct_engineering_task" not in
                getattr(operations, "SUPPORTED", ()) or not adapter or
                not adapter.registered_target("service:chatgpt", principal_kind="service")):
            raise ValueError("delegation_request_target_unavailable")
        return adapter.request_grant(requester_id=principal_id, principal_id="service:chatgpt",
            action=action, scope_ref=DELEGATED_PROJECT_SCOPE, policy_ref=DELEGATED_POLICY,
            request_ref=data["purpose"].strip(), max_uses=None, valid_until=valid_until,
            idempotency_key=idempotency_key)
    raise ValueError("delegation_request_type_unavailable")


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
    if handler.command == "POST" and _DECISION.fullmatch(parsed.path):
        try:
            principal_id, _ = _request_context(handler)
            data = handler._json_body(8 * 1024)
            required = {"decision", "expected_request_sha256", "idempotency_key"}
            if (not required <= set(data) or set(data) - required - {"approval_ref"} or
                    data["decision"] not in {"approve", "reject"} or
                    not isinstance(data["expected_request_sha256"], str) or
                    not re.fullmatch(r"[0-9a-f]{64}", data["expected_request_sha256"]) or
                    not isinstance(data["idempotency_key"], str) or
                    not re.fullmatch(r"[A-Za-z0-9._:-]{16,200}", data["idempotency_key"])):
                raise ValueError("delegation_decision_fields_invalid")
            approval_ref = data.get("approval_ref")
            if data["decision"] == "approve":
                if not isinstance(approval_ref, str) or not 1 <= len(approval_ref.strip()) <= 256:
                    raise ValueError("delegation_approval_reference_required")
                approval_ref = approval_ref.strip()
            elif approval_ref is not None:
                raise ValueError("delegation_rejection_must_not_include_approval_reference")
            operations = getattr(handler.server, "_comms5_operations", None)
            adapter = getattr(operations, "delegation_grant_requests", None) if operations else None
            if adapter is None:
                raise RuntimeError("delegation_authority_unavailable")
            result = adapter.decide_request(authenticated_steward_id=principal_id,
                request_id=_DECISION.fullmatch(parsed.path).group(1),
                decision=data["decision"],
                expected_request_sha256=data["expected_request_sha256"],
                idempotency_key=data["idempotency_key"], approval_ref=approval_ref)
            handler._json(200, result, request_id)
        except PermissionError:
            handler._error(403, "steward_authority_denied", request_id)
        except (ValueError, TypeError, json.JSONDecodeError):
            handler._error(400, "invalid_delegation_decision", request_id)
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
                handler._error(503, "delegation_decision_unavailable", request_id)
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

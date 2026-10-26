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
import re
from urllib.parse import parse_qs

from .delegation_projection import get_request, list_grants, list_requests, revoke_grant


_REQUEST = re.compile(r"^/api/v1/steward/delegation-grant-requests/(delegation-request:[A-Za-z0-9._:-]{1,128})$")
_REVOKE = re.compile(r"^/api/v1/steward/delegated-grants/(grant:[A-Za-z0-9._:-]{1,128})/revoke$")
_REQUESTS = "/api/v1/steward/delegation-grant-requests"
_GRANTS = "/api/v1/steward/delegated-grants"


def is_route(method: str, path: str) -> bool:
    return ((method in {"GET", "HEAD"} and
             (path in {_REQUESTS, _GRANTS} or _REQUEST.fullmatch(path) is not None)) or
            (method == "POST" and _REVOKE.fullmatch(path) is not None))


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

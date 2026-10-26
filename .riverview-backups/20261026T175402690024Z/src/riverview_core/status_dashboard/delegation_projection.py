# Riverview~ Controlled Source
# File: src/riverview_core/status_dashboard/delegation_projection.py
# Component: STEWARD-DELEGATION-APPROVAL-PROJECTION
# Revision: 1.0.0
# Purpose: Read and revoke canonical delegated authority through the protected Steward adapter
# Execution Model: Request-driven, bounded read projection and explicit revocation
# Observability: Safe route errors; canonical authority audit events
# Dependencies: Existing Comms5DelegationAuthorityAdapter and institutional authority tables
# Authority: Authenticated institutional Steward with authority.grant at institution scope
# Changed: 2026-10-26 UTC | RV-V2-DELEGATION-PROJECTION-001 | Add bounded request/grant read projections and canonical revocation.
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# Tests: tests/test_delegation_projection.py
# History: Initial controlled source
"""Steward-only projections of canonical delegation requests and grants."""

from __future__ import annotations

import re
from datetime import datetime

from riverview_core.institutional_authority.registry import (
    AuthorityDenied, IdentityConflict, RegistryUnavailable,
)


_STATUSES = {"pending", "approved", "rejected"}
_GRANT_STATES = {"active", "expired", "revoked"}
_REQUEST_ID = re.compile(r"^delegation-request:[A-Za-z0-9._:-]{1,128}$")
_GRANT_ID = re.compile(r"^grant:[A-Za-z0-9._:-]{1,128}$")


def _context(adapter):
    if adapter is None or not callable(getattr(adapter, "_authenticated_steward", None)):
        raise PermissionError("steward_authority_unavailable")
    principal = adapter._authenticated_steward()
    if principal != "steward:camrui":
        raise PermissionError("authenticated_steward_required")
    registry = getattr(adapter, "_registry", None)
    token = getattr(adapter, "_steward_token", None)
    if registry is None or not isinstance(token, str) or len(token) < 32:
        raise RuntimeError("delegation_authority_unavailable")
    return registry, token


def _require_authority(cur, registry, token):
    registry._path(cur)
    actor = registry._require(cur, token, "authority.grant", "institution")
    if actor.get("principal_kind") != "steward" or actor.get("principal_id") != "steward:camrui":
        raise PermissionError("steward_authority_denied")


def _record(row):
    result = dict(row)
    for key, value in tuple(result.items()):
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def _event_refs(cur, request_ids=(), grant_ids=()):
    if not request_ids and not grant_ids:
        return {}
    cur.execute("""SELECT event_id::text AS event_id,event_type,grant_id,recorded_at,
        payload->>'request_id' AS request_id
        FROM institutional_authority_events
        WHERE payload->>'request_id'=ANY(%s) OR grant_id=ANY(%s)
        ORDER BY recorded_at,event_id""", (list(request_ids), list(grant_ids)))
    result = {}
    for row in cur.fetchall():
        item = _record(row)
        key = item.get("request_id") or item.get("grant_id")
        if key:
            result.setdefault(key, []).append({
                "event_id": item["event_id"], "event_type": item["event_type"],
                "recorded_at": item["recorded_at"],
            })
    return result


def list_requests(adapter, *, status="pending", limit=50):
    """Read a bounded request list from the canonical authority registry."""
    if status not in {*_STATUSES, "all"}:
        raise ValueError("delegation_request_status_invalid")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("delegation_request_limit_invalid")
    registry, token = _context(adapter)
    try:
        with registry.db.transaction():
            with registry.db.cursor() as cur:
                _require_authority(cur, registry, token)
                if status == "all":
                    cur.execute("""SELECT request_id,request_kind,requester_id,grantee_id,
                        change_grant_id,action,scope_ref,policy_ref,request_ref,max_uses,
                        valid_until,duration_spec,change_kind,request_sha256,status,decision,decision_by,decision_at,
                        approval_ref,grant_id,created_at FROM delegated_grant_requests
                        ORDER BY created_at DESC,request_id DESC LIMIT %s""", (limit,))
                else:
                    cur.execute("""SELECT request_id,request_kind,requester_id,grantee_id,
                        change_grant_id,action,scope_ref,policy_ref,request_ref,max_uses,
                        valid_until,duration_spec,change_kind,request_sha256,status,decision,decision_by,decision_at,
                        approval_ref,grant_id,created_at FROM delegated_grant_requests
                        WHERE status=%s ORDER BY created_at DESC,request_id DESC LIMIT %s""",
                        (status, limit))
                items = [_record(row) for row in cur.fetchall()]
                refs = _event_refs(cur, request_ids=[row["request_id"] for row in items])
                for item in items:
                    item["audit_events"] = refs.get(item["request_id"], [])
                return {"status": "available", "filter": status, "limit": limit,
                        "items": items}
    except (AuthorityDenied, IdentityConflict, PermissionError, ValueError):
        raise
    except Exception as exc:
        raise RegistryUnavailable(type(exc).__name__) from None


def get_request(adapter, request_id):
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        raise ValueError("delegation_request_id_invalid")
    _context(adapter)
    result = adapter.get_status(requester_id="steward:camrui", request_id=request_id)
    registry, token = _context(adapter)
    with registry.db.transaction():
        with registry.db.cursor() as cur:
            _require_authority(cur, registry, token)
            refs = _event_refs(cur, request_ids=[request_id])
    item = _record(result)
    item["audit_events"] = refs.get(request_id, [])
    return item


def list_grants(adapter, *, state="active", limit=50):
    """Inspect delegated grants without creating or editing authority."""
    if state not in {*_GRANT_STATES, "all"}:
        raise ValueError("delegation_grant_state_invalid")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("delegation_grant_limit_invalid")
    registry, token = _context(adapter)
    try:
        with registry.db.transaction():
            with registry.db.cursor() as cur:
                _require_authority(cur, registry, token)
                state_clause = {
                    "active": "AND revoked_at IS NULL AND (valid_until IS NULL OR valid_until > clock_timestamp())",
                    "expired": "AND revoked_at IS NULL AND valid_until <= clock_timestamp()",
                    "revoked": "AND revoked_at IS NOT NULL",
                    "all": "",
                }[state]
                cur.execute(f"""SELECT grant_id,principal_id,action,scope_ref,policy_ref,
                    valid_until,duration_spec,supersedes_grant_id,max_uses,used_count,grant_kind,proposal_ref,proposal_digest,
                    approved_by,approved_at,approval_ref,revoked_at
                    FROM authority_grants WHERE grant_kind='delegated'
                    {state_clause}
                    ORDER BY approved_at DESC NULLS LAST,grant_id DESC LIMIT %s""", (limit,))
                grants = [_record(row) for row in cur.fetchall()]
                refs = _event_refs(cur, grant_ids=[item["grant_id"] for item in grants])
                for item in grants:
                    if item.get("revoked_at"):
                        grant_state = "revoked"
                    elif item.get("valid_until") and datetime.fromisoformat(
                            item["valid_until"]) <= datetime.now().astimezone():
                        grant_state = "expired"
                    else:
                        grant_state = "active"
                    item["state"] = grant_state
                    item["audit_events"] = refs.get(item["grant_id"], [])
                return {"status": "available", "filter": state, "limit": limit,
                        "items": grants}
    except (AuthorityDenied, IdentityConflict, PermissionError, ValueError):
        raise
    except Exception as exc:
        raise RegistryUnavailable(type(exc).__name__) from None


def revoke_grant(adapter, grant_id, *, confirm, reason_code="steward_revoked"):
    """Revoke through the existing audited authority registry; never issue grants."""
    if not isinstance(grant_id, str) or not _GRANT_ID.fullmatch(grant_id):
        raise ValueError("delegation_grant_id_invalid")
    if confirm is not True:
        raise ValueError("explicit_confirmation_required")
    if not isinstance(reason_code, str) or not re.fullmatch(r"[a-z0-9_]{1,64}", reason_code):
        raise ValueError("delegation_revoke_reason_invalid")
    registry, token = _context(adapter)
    return registry.revoke_grant(token, grant_id, reason_code=reason_code)

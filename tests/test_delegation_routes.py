# Riverview~ Controlled Source
# File: tests/test_delegation_routes.py
# Component: STEWARD-DELEGATION-APPROVAL-API
# Revision: 1.0.0
# Purpose: Verify narrow Steward delegation API routing and composite-source overlay
# Execution Model: Local unittest with fake account and authority adapters
# Observability: unittest case names, counts and exit status
# Dependencies: Python standard library and isolated Riverview test modules
# Authority: Synthetic Steward identity and fake canonical registry only
# Changed: 2026-10-26 UTC | RV-V2-DELEGATION-PROJECTION-001 | Cover endpoint method/identity fences and patch idempotence.
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# History: Initial controlled source
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from riverview_core.status_dashboard.delegation_projection import (
    list_grants, list_requests, revoke_grant,
)
from riverview_core.status_dashboard.delegation_routes import dispatch, is_route
from scripts.apply_delegation_projection_overlay import apply


ROOT = Path(__file__).resolve().parents[1]
BASE = "5f4826caf9077147fefe2e3d9882ff835ffec9c3"


class _Cursor:
    def __init__(self, registry):
        self.registry = registry
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.registry.queries.append((query, params))
        if "FROM delegated_grant_requests" in query:
            self.rows = [dict(self.registry.request)]
        elif "FROM authority_grants" in query:
            self.rows = [dict(self.registry.grant)]
        elif "FROM institutional_authority_events" in query:
            self.rows = [dict(self.registry.event)]
        else:
            self.rows = []

    def fetchall(self):
        return self.rows


class _Registry:
    def __init__(self, actor="steward"):
        self.actor = actor
        self.queries = []
        self.request = {"request_id":"delegation-request:test-1","status":"pending",
            "request_sha256":"a"*64,"request_ref":"work-order:eng-demo",
            "action":"objective.submit","scope_ref":"institution",
            "requester_id":"resident:grace","grantee_id":"resident:grace",
            "request_kind":"grant","policy_ref":"policy:delegation.v1",
            "created_at":None,"grant_id":None}
        self.grant = {"grant_id":"grant:test-1","principal_id":"resident:grace",
            "action":"objective.submit","scope_ref":"institution","policy_ref":"policy:delegation.v1",
            "valid_until":None,"max_uses":None,"used_count":0,"grant_kind":"delegated",
            "proposal_ref":None,"proposal_digest":None,"approved_by":"steward:camrui",
            "approved_at":None,"approval_ref":"fixture","revoked_at":None}
        self.event = {"event_id":"event-test-1","event_type":"authority_delegation_request_created",
            "grant_id":None,"recorded_at":None,"request_id":"delegation-request:test-1"}
        self.db = self

    def transaction(self):
        return self

    def cursor(self):
        return _Cursor(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def _path(self, cur):
        pass

    def _require(self, cur, token, action, scope):
        if self.actor != "steward":
            raise PermissionError("denied")
        self.required = (action, scope)
        return {"principal_kind":"steward","principal_id":"steward:camrui"}

    def revoke_grant(self, token, grant_id, *, reason_code):
        self.revoked = (grant_id, reason_code)
        return {"status":"revoked"}


class _Adapter:
    def __init__(self, actor="steward"):
        self._registry = _Registry(actor)
        self._steward_token = "s" * 64

    def _authenticated_steward(self):
        return "steward:camrui" if self._registry.actor == "steward" else "resident:grace"

    def get_status(self, *, requester_id, request_id=None, grant_id=None):
        return dict(self._registry.request)


class _Handler:
    command = "GET"

    def __init__(self, adapter, *, identity=None, cookie=True, body=None):
        self._account_cookie_authenticated = cookie
        self._account_identity = identity or {"roles":["steward"],
            "authority_principal_id":"steward:camrui"}
        self.server = SimpleNamespace(_comms5_operations=SimpleNamespace(
            delegation_grant_requests=adapter))
        self.body = body or {}
        self.response = None

    def _json(self, status, payload, request_id):
        self.response = (status, payload)

    def _error(self, status, code, request_id):
        self.response = (status, {"error":code})

    def _json_body(self, maximum):
        return self.body


class DelegationProjectionTests(unittest.TestCase):
    def test_pending_projection_includes_exact_hash_scope_and_audit_event(self):
        adapter = _Adapter()
        result = list_requests(adapter, status="pending", limit=10)
        self.assertEqual(result["items"][0]["request_sha256"], "a"*64)
        self.assertEqual(result["items"][0]["scope_ref"], "institution")
        self.assertEqual(result["items"][0]["audit_events"][0]["event_id"], "event-test-1")
        self.assertEqual(adapter._registry.required, ("authority.grant", "institution"))

    def test_grant_state_filters_are_applied_before_the_bounded_limit(self):
        for state, clause in (("active", "valid_until > clock_timestamp()"),
                              ("expired", "valid_until <= clock_timestamp()"),
                              ("revoked", "revoked_at IS NOT NULL"),
                              ("all", "ORDER BY approved_at")):
            adapter = _Adapter()
            result = list_grants(adapter, state=state, limit=10)
            query = next(query for query, _ in adapter._registry.queries
                         if "FROM authority_grants" in query)
            self.assertIn(clause, query)
            self.assertEqual(result["filter"], state)
            self.assertIn("LIMIT %s", query)

    def test_registry_requires_steward_and_revoke_requires_confirmation(self):
        with self.assertRaises(PermissionError):
            list_grants(_Adapter("resident"), state="all")
        with self.assertRaisesRegex(ValueError, "explicit_confirmation_required"):
            revoke_grant(_Adapter(), "grant:test-1", confirm=False)
        adapter = _Adapter()
        self.assertEqual(revoke_grant(adapter, "grant:test-1", confirm=True), {"status":"revoked"})
        self.assertEqual(adapter._registry.revoked, ("grant:test-1", "steward_revoked"))

    def test_routes_are_exact_and_never_turn_get_into_revoke(self):
        self.assertTrue(is_route("GET", "/api/v1/steward/delegation-grant-requests"))
        self.assertTrue(is_route("GET", "/api/v1/steward/delegation-grant-requests/delegation-request:abc"))
        self.assertTrue(is_route("GET", "/api/v1/steward/delegated-grants"))
        self.assertTrue(is_route("POST", "/api/v1/steward/delegated-grants/grant:abc/revoke"))
        self.assertFalse(is_route("POST", "/api/v1/steward/delegation-grant-requests/delegation-request:abc/decision"))
        self.assertFalse(is_route("POST", "/api/v1/steward/delegated-grants/../revoke"))

    def test_route_rejects_unlinked_steward_and_requires_server_confirmation(self):
        adapter = _Adapter()
        denied = _Handler(adapter, identity={"roles":["steward"],"authority_principal_id":"steward:other"})
        self.assertTrue(dispatch(denied, SimpleNamespace(path="/api/v1/steward/delegation-grant-requests",query=""), "r"))
        self.assertEqual(denied.response[0], 403)
        no_cookie = _Handler(adapter, cookie=False)
        dispatch(no_cookie, SimpleNamespace(path="/api/v1/steward/delegated-grants",query=""), "r")
        self.assertEqual(no_cookie.response[0], 403)
        handler = _Handler(adapter, body={"confirm":False})
        handler.command = "POST"
        dispatch(handler, SimpleNamespace(path="/api/v1/steward/delegated-grants/grant:test-1/revoke",query=""), "r")
        self.assertEqual(handler.response[0], 400)

    def test_overlay_is_idempotent_and_fails_closed_on_unknown_source(self):
        source = subprocess.check_output(["git","show",f"{BASE}:src/riverview_core/status_dashboard/server.py"],
                                         cwd=ROOT,text=True)
        patched = apply(source)
        self.assertEqual(apply(patched), patched)
        compile(patched, "candidate-server.py", "exec")
        self.assertEqual(patched.count("delegation_routes import dispatch"), 1)
        with self.assertRaisesRegex(ValueError, "snapshot_dispatch_anchor_not_unique"):
            apply("unrecognized source")


if __name__ == "__main__":
    unittest.main()

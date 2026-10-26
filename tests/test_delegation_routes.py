# Riverview~ Controlled Source
# File: tests/test_delegation_routes.py
# Component: STEWARD-DELEGATION-APPROVAL-API
# Revision: 1.0.3
# Purpose: Verify narrow Steward delegation API routing and composite-source overlay
# Execution Model: Local unittest with fake account and authority adapters
# Observability: unittest case names, counts and exit status
# Dependencies: Python standard library and isolated Riverview test modules
# Authority: Synthetic Steward identity and fake canonical registry only
# Changed: 2026-10-26 UTC | RV-V2-DELEGATION-PROJECTION-001 | Cover endpoint method/identity fences and patch idempotence.
# Changed: 2026-10-26 UTC | RV-ISSUE268-DELEGATION-CANCEL-ACCEPTANCE | Cover isolated Steward principal binding, canonical projection and 24-hour activation policy.
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
# History: Initial controlled source
import subprocess
import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import urlsplit
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
            from riverview_core.institutional_authority.registry import AuthorityDenied
            raise AuthorityDenied("denied")
        self.required = (action, scope)
        return {"principal_kind":"steward","principal_id":"steward:camrui"}

    def authorize(self, token, action, scope):
        return self._require(self, token, action, scope)

    def revoke_grant(self, token, grant_id, *, reason_code):
        self.revoked = (grant_id, reason_code)
        return {"status":"revoked"}


class _Adapter:
    def __init__(self, actor="steward", registry=None):
        self._registry = registry or _Registry(actor)
        self._steward_token = "s" * 64

    def _authenticated_steward(self):
        return "steward:camrui" if getattr(self._registry,"actor","steward") == "steward" else "resident:grace"

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


class _RequestTelemetry:
    def read(self):
        return {"hosts":[{"host_id":"octominer1","display_name":"OCTOMINER1",
                          "identity_state":"verified"},
                         {"host_id":"octominer2","display_name":"OctoMiner2",
                          "identity_state":"documented_unverified"}]}
    def workload_controller_registrations(self):
        return {"octominer1":{"services":[{"service_id":"vision","display_name":"Vision"}],
                "capabilities":[{"capability_id":f"hardware.gpu.workload.{x}",
                                  "action":f"hardware.gpu.workload.{x}"}
                                 for x in ("read","start","stop","switch")]}}


class _RequestPermissionStore:
    def list_profiles(self, principal_id):
        return {"capabilities":[{"capability_id":f"hardware.gpu.workload.{action}",
                    "authority_action":f"hardware.gpu.workload.{action}","enabled":True,
                    "registration_blocker":None,"description":f"Registered {action} operation"}
                for action in ("read","start","stop","switch")]}


class _RequestRegistry:
    def __init__(self): self.auth=[]; self.created=[]
    def authorize(self, token, action, scope):
        self.auth.append((token,action,scope))
        if action!="authority.grant" or scope!="institution":
            from riverview_core.institutional_authority.registry import AuthorityDenied
            raise AuthorityDenied("not allowed")
        return {"principal_id":"steward:camrui","principal_kind":"steward"}
    def request_grant(self, **kwargs): self.created.append(kwargs); return {
        "status":"pending","request_id":"delegation-request:fixture-1","request_sha256":"a"*64}


class DelegationRequestCreationTests(unittest.TestCase):
    def handler(self, registry, body=None, *, roles=("steward",), cookie=True):
        adapter=_Adapter(registry=registry)
        handler=_Handler(adapter)
        handler.command="POST"
        handler._account_cookie_authenticated=cookie
        handler._account_identity={"roles":list(roles),"authority_principal_id":"steward:camrui"}
        adapter.registered_target = lambda principal_id, *, principal_kind=None: False
        handler.server=SimpleNamespace(_authority_registry=registry,_resource_telemetry=_RequestTelemetry(),
                                       _permission_store=_RequestPermissionStore(),
                                       _comms5_operations=SimpleNamespace(delegation_grant_requests=adapter))
        handler.body=body or {}
        return handler

    def body(self, **overrides):
        value={"authorization_type_id":"gpu_host","host_id":"octominer1",
               "action":"hardware.gpu.workload.switch","max_uses":3,
               "purpose":"Operate approved OCTOMINER1 workload switching controls",
               "valid_until":(datetime.now(timezone.utc)+timedelta(days=7)).isoformat(),
               "idempotency_key":"test-request-key-0001"}
        value.update(overrides); return value

    def test_registered_host_options_are_exact_and_unverified_host_is_excluded(self):
        registry=_RequestRegistry(); handler=self.handler(registry)
        handler.server._comms5_operations.SUPPORTED={"comms5_submit_direct_engineering_task"}
        handler.command="GET"; handler.body={}
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                self.assertTrue(is_route("GET","/api/v1/steward/delegation-grant-requests/options"))
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests/options"),"r")
        self.assertEqual(handler.response[0],200)
        self.assertEqual([x["host_id"] for x in handler.response[1]["hosts"]],["octominer1"])
        self.assertEqual(handler.response[1]["hosts"][0]["scope_ref"],"host:octominer1")
        self.assertEqual(handler.response[1]["authorization_types"][0]["max_expiry_days"],365)
        self.assertTrue(handler.response[1]["authorization_types"][0]["non_expiring_supported"])
        self.assertTrue(handler.response[1]["authorization_types"][0]["non_expiring_requires_usage_limit"])
        self.assertEqual(handler.response[1]["authorization_types"][1]["status"],"unavailable")
        self.assertEqual(handler.response[1]["authorization_types"][1]["unavailable_reason"],
                         "target_principal_not_registered_active")
        self.assertEqual([x["capability_id"] for x in handler.response[1]["hosts"][0]["capabilities"]],
            [f"hardware.gpu.workload.{x}" for x in ("read","start","stop","switch")])
        self.assertTrue(all(item["description"].startswith("Registered")
                            for item in handler.response[1]["hosts"][0]["capabilities"]))

    def test_codex_request_type_reports_missing_executor_separately_from_identity(self):
        registry=_RequestRegistry(); handler=self.handler(registry)
        handler.command="GET"; handler.body={}
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests/options"),"r")
        self.assertEqual(handler.response[0],200)
        codex=next(item for item in handler.response[1]["authorization_types"]
                   if item["type_id"]=="comms5_codex")
        self.assertEqual(codex["unavailable_reason"],"codex_task_operation_not_registered")

    def test_chatgpt_registration_options_require_identity_manage_and_protected_sink(self):
        registry = _Registry()
        adapter = _Adapter(registry=registry)
        adapter.registered_target = lambda principal_id, *, principal_kind=None: False
        adapter.chatgpt_registration_available = lambda: True
        handler = self.handler(registry)
        handler.server._comms5_operations = SimpleNamespace(
            delegation_grant_requests=adapter,
            SUPPORTED={"comms5_submit_direct_engineering_task"})
        handler.server._resource_telemetry = _RequestTelemetry()
        handler.server._permission_store = _RequestPermissionStore()
        handler.command = "GET"
        dispatch(handler, urlsplit("/api/v1/steward/delegation-grant-requests/options"), "r")
        registration = handler.response[1]["chatgpt_registration"]
        self.assertEqual(registration["principal_id"], "service:chatgpt")
        self.assertEqual(registration["required_action"], "identity.manage")
        self.assertEqual(registration["required_scope"], "institution")
        self.assertTrue(registration["available"])
        self.assertFalse(registration["credential_shown_to_browser"])

    def test_registration_requires_identity_manage_and_exact_confirmation(self):
        registry = _Registry()
        adapter = _Adapter(registry=registry)
        adapter.register_chatgpt_service_principal = lambda: {
            "status": "registered", "principal_id": "service:chatgpt",
            "principal_kind": "service", "credential_stored": True}
        handler = _Handler(adapter, body={"confirmation": "REGISTER service:chatgpt"})
        handler.command = "POST"
        path = "/api/v1/steward/service-principals/chatgpt/register"
        self.assertTrue(is_route("POST", path))
        dispatch(handler, urlsplit(path), "r")
        self.assertEqual(handler.response[0], 201)
        self.assertEqual(registry.required, ("identity.manage", "institution"))
        self.assertNotIn("credential", handler.response[1])

        invalid = _Handler(adapter, body={"confirmation": "register"})
        invalid.command = "POST"
        dispatch(invalid, urlsplit(path), "r")
        self.assertEqual(invalid.response[0], 400)

        denied_registry = _Registry(actor="resident")
        denied_adapter = _Adapter(registry=denied_registry)
        denied_adapter.register_chatgpt_service_principal = lambda: self.fail(
            "unauthorized request must not call the registry")
        denied = _Handler(denied_adapter,
            body={"confirmation": "REGISTER service:chatgpt"})
        denied.command = "POST"
        dispatch(denied, urlsplit(path), "r")
        self.assertEqual(denied.response[0], 403)

    def test_isolated_steward_identity_is_bound_to_its_canonical_authority(self):
        """The reserved browser persona can use a disposable canonical Steward identity."""
        class IsolatedRegistry(_Registry):
            def authorize(self, token, action, scope):
                self.required = (action, scope)
                if action not in {"authority.grant", "identity.manage"} or scope != "institution":
                    from riverview_core.institutional_authority.registry import AuthorityDenied
                    raise AuthorityDenied("missing isolated Steward grant")
                return {"principal_id":"steward:test", "principal_kind":"steward"}

        registry = IsolatedRegistry()
        adapter = _Adapter(registry=registry)
        adapter._authenticated_steward = lambda: "steward:test"
        adapter.register_chatgpt_service_principal = lambda: {
            "status":"registered", "principal_id":"service:chatgpt",
            "principal_kind":"service", "credential_stored":True}
        handler = _Handler(adapter, identity={"roles":["steward"],
                            "authority_principal_id":"steward:test"},
                           body={"confirmation":"REGISTER service:chatgpt"})
        handler.command = "POST"
        path = "/api/v1/steward/service-principals/chatgpt/register"
        self.assertTrue(dispatch(handler, urlsplit(path), "isolated"))
        self.assertEqual(handler.response[0], 201)
        self.assertNotIn("credential", handler.response[1])
        self.assertEqual(registry.required, ("identity.manage", "institution"))

        # The same authority token cannot be paired with a different account principal.
        mismatched = _Handler(adapter, identity={"roles":["steward"],
                               "authority_principal_id":"steward:other"},
                              body={"confirmation":"REGISTER service:chatgpt"})
        mismatched.command = "POST"
        self.assertTrue(dispatch(mismatched, urlsplit(path), "isolated-mismatch"))
        self.assertEqual(mismatched.response[0], 403)

    def test_request_submission_is_pending_exact_scope_and_requires_steward_authority(self):
        registry=_RequestRegistry(); handler=self.handler(registry,self.body())
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],201)
        self.assertEqual(handler.response[1]["status"],"pending")
        self.assertEqual(registry.created[0]["scope_ref"],"host:octominer1")
        self.assertEqual(registry.created[0]["action"],"hardware.gpu.workload.switch")
        self.assertEqual(registry.created[0]["principal_id"],"steward:camrui")
        self.assertEqual(registry.created[0]["request_ref"],self.body()["purpose"])
        self.assertEqual(registry.created[0]["max_uses"],3)

    def test_gpu_request_supports_one_use_and_combined_expiry_and_usage_bounds(self):
        registry=_RequestRegistry(); handler=self.handler(registry,self.body(max_uses=1,
            valid_until=(datetime.now(timezone.utc)+timedelta(days=365)).isoformat()))
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],201)
        self.assertEqual(registry.created[0]["max_uses"],1)
        self.assertEqual(registry.created[0]["valid_until"].date(),
                         datetime.fromisoformat(self.body(valid_until=(datetime.now(timezone.utc)+timedelta(days=365)).isoformat())["valid_until"]).date())

    def test_gpu_request_supports_expiry_without_use_count(self):
        expiry=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()
        registry=_RequestRegistry(); handler=self.handler(registry,self.body(max_uses=None,valid_until=expiry))
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],201)
        self.assertIsNone(registry.created[0]["max_uses"])
        self.assertIsNotNone(registry.created[0]["valid_until"])

    def test_gpu_request_supports_finite_usage_without_expiry(self):
        registry=_RequestRegistry(); handler=self.handler(registry,self.body(max_uses=1,valid_until=None))
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],201)
        self.assertEqual(registry.created[0]["max_uses"],1)
        self.assertIsNone(registry.created[0]["valid_until"])

    def test_unlimited_nonexpiring_request_is_rejected_before_registry_write(self):
        registry=_RequestRegistry(); handler=self.handler(registry,self.body(max_uses=None,valid_until=None))
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],400)
        self.assertEqual(registry.created,[])

    def test_comms5_codex_target_requires_registered_service_identity_and_uses_project_scope(self):
        class DelegationAdapter:
            def __init__(self, active, registry):
                self.active=active; self.created=[]; self._registry=registry
                self._steward_token="s"*64
            def _authenticated_steward(self): return "steward:camrui"
            def registered_target(self, principal_id, *, principal_kind=None):
                return self.active and principal_id=="service:chatgpt" and principal_kind=="service"
            def request_grant(self, **kwargs):
                self.created.append(kwargs)
                return {"status":"pending","request_id":"delegation-request:codex-test",
                        "request_sha256":"b"*64}
        registry=_RequestRegistry(); adapter=DelegationAdapter(True,registry)
        handler=self.handler(registry,{
            "authorization_type_id":"comms5_codex","action":"comms5.operations.non_destructive.v1",
            "purpose":"Allow the existing Comms5 Codex task submission path",
            "valid_until":None,
            "max_uses":None,"idempotency_key":"codex-delegation-key-0001"})
        handler.server._comms5_operations=SimpleNamespace(
            delegation_grant_requests=adapter,
            SUPPORTED={"comms5_submit_direct_engineering_task"})
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],201)
        self.assertEqual(adapter.created[0]["principal_id"],"service:chatgpt")
        self.assertEqual(adapter.created[0]["scope_ref"],"project:Riverview")
        self.assertEqual(adapter.created[0]["max_uses"],None)
        self.assertIsNone(adapter.created[0]["valid_until"])
        self.assertEqual(adapter.created[0]["duration_spec"],{"unit":"hours","value":24})

    def test_comms5_codex_target_is_not_requestable_without_registered_identity(self):
        class DelegationAdapter:
            def __init__(self, registry):
                self._registry=registry; self._steward_token="s"*64
            def _authenticated_steward(self): return "steward:camrui"
            def registered_target(self, principal_id, *, principal_kind=None): return False
            def request_grant(self, **kwargs): raise AssertionError("must not submit")
        registry=_RequestRegistry(); handler=self.handler(registry,{
            "authorization_type_id":"comms5_codex","action":"comms5.operations.non_destructive.v1",
            "purpose":"Allow the existing Comms5 Codex task submission path",
            "valid_until":None,
            "max_uses":None,"idempotency_key":"codex-delegation-key-0002"})
        handler.server._comms5_operations=SimpleNamespace(
            delegation_grant_requests=DelegationAdapter(registry),
            SUPPORTED={"comms5_submit_direct_engineering_task"})
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],400)

    def test_decision_route_preserves_hash_idempotency_and_confirmation_reference(self):
        class DecisionAdapter(_Adapter):
            def __init__(self, registry):
                super().__init__(registry=registry); self.decisions=[]; self.stale=False
            def decide_request(self, **kwargs):
                self.decisions.append(kwargs)
                if self.stale:
                    from riverview_core.institutional_authority.registry import IdentityConflict
                    raise IdentityConflict("request hash changed")
                return {"status":"approved","request_id":kwargs["request_id"],"grant_id":"grant:fixture"}
        registry=_RequestRegistry(); adapter=DecisionAdapter(registry)
        handler=self.handler(registry,{
            "decision":"approve","expected_request_sha256":"a"*64,
            "idempotency_key":"decision-idempotency-0001","approval_ref":"acceptance fixture"})
        handler.server._comms5_operations=SimpleNamespace(delegation_grant_requests=adapter)
        path="/api/v1/steward/delegation-grant-requests/delegation-request:fixture/decision"
        self.assertTrue(is_route("POST",path))
        self.assertTrue(dispatch(handler,urlsplit(path),"r"))
        self.assertEqual(handler.response[0],200)
        self.assertEqual(adapter.decisions[0]["expected_request_sha256"],"a"*64)
        self.assertEqual(adapter.decisions[0]["approval_ref"],"acceptance fixture")
        adapter.stale=True
        handler=self.handler(registry,{
            "decision":"approve","expected_request_sha256":"b"*64,
            "idempotency_key":"decision-idempotency-0002","approval_ref":"stale fixture"})
        handler.server._comms5_operations=SimpleNamespace(delegation_grant_requests=adapter)
        self.assertTrue(dispatch(handler,urlsplit(path),"r"))
        self.assertEqual(handler.response[0],409)

    def test_unregistered_host_and_non_steward_cannot_create_requests(self):
        registry=_RequestRegistry(); handler=self.handler(registry,self.body(host_id="octominer2"))
        with tempfile.TemporaryDirectory() as root:
            Path(root,"authority-steward-token").write_text("t"*64)
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}):
                dispatch(handler,urlsplit("/api/v1/steward/delegation-grant-requests"),"r")
        self.assertEqual(handler.response[0],400)
        self.assertEqual(registry.created,[])
        denied=self.handler(_RequestRegistry(),self.body(),roles=("resident",))
        self.assertEqual(dispatch(denied,urlsplit("/api/v1/steward/delegation-grant-requests"),"r"),True)
        self.assertEqual(denied.response[0],403)
        self.assertEqual(denied.server._authority_registry.created,[])


class DelegationProjectionTests(unittest.TestCase):
    def test_isolated_steward_can_read_only_its_matching_canonical_projection(self):
        class IsolatedRegistry(_Registry):
            def _require(self, cur, token, action, scope):
                self.required = (action, scope)
                return {"principal_kind":"steward", "principal_id":"steward:test"}

        registry = IsolatedRegistry()
        adapter = _Adapter(registry=registry)
        adapter._authenticated_steward = lambda: "steward:test"
        requests = list_requests(adapter, status="pending", limit=10)
        grants = list_grants(adapter, state="all", limit=10)
        self.assertEqual(requests["items"][0]["request_id"], "delegation-request:test-1")
        self.assertEqual(grants["items"][0]["grant_id"], "grant:test-1")
        self.assertEqual(registry.required, ("authority.grant", "institution"))

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
        from riverview_core.institutional_authority.registry import AuthorityDenied
        with self.assertRaises((PermissionError, AuthorityDenied)):
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
        self.assertTrue(is_route("POST", "/api/v1/steward/delegation-grant-requests/delegation-request:abc/decision"))
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

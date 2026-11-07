# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_grace_capability_registry.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.1
# Changed: 2026-10-25 UTC | C3-AUTOMATIC-CAPABILITY-REGISTRATION | Test declaration blockers and dynamic capability metadata
# Purpose: Verify dynamic institutional capability discovery and exact-grant invocation
# Execution Model: Isolated database, authority, worker and pipeline fixtures
# Observability: Assertions over tool schemas, exact authorization, results and updates
# Authority: Test doubles only; no production credentials or database access
# Tests: python -m unittest tests.test_grace_capability_registry
# =============================================================================
"""Dynamic discovery and exact-grant enforcement for Grace's registry bridge."""

import json
import unittest
from datetime import datetime, timezone

from riverview_core.resident_execution.capability_registry import GraceCapabilityRegistry
from riverview_core.resident_execution.internal_tools import GraceInternalTools
from riverview_core.resident_execution.model_router import GraceModelRouter
from riverview_core.institutional_authority.grants import GrantDenied
from riverview_core.local_reasoning_provider import ChatCompletion, ProviderReadiness


class _Cursor:
    def __init__(self, state):
        self.state = state
        self.row = None

    def __enter__(self): return self
    def __exit__(self, *_): return False

    def execute(self, query, params=None):
        query = str(query)
        if "list_capability_registry" in query:
            self.row = [(json.loads(json.dumps(self.state.catalog)),)]
        elif "list_capability_grants" in query:
            self.row = list(self.state.grants)
        elif "worker_registry" in query:
            self.row = []
        elif "grace_execution_health" in query:
            self.row = [("healthy", [], datetime.now(timezone.utc), "grace.execution.v1")]
        else:
            raise AssertionError("unexpected registry SQL")

    def fetchone(self):
        return self.row[0] if self.row else None

    def fetchall(self):
        return self.row


class _Connection:
    def __init__(self, state): self.state = state
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def cursor(self): return _Cursor(self.state)


class _Authorizer:
    @staticmethod
    def require(_cursor, _credential, action, scope):
        if (action, scope) not in {
                ("office.state.write", "office:office:grace"),
                ("objective.submit", "work-order:engineering"),
                ("resident.status.read", "institution:riverview"),
                ("pending.website.account.session.read", "institution:riverview")}:
            raise GrantDenied("exact grant missing")
        grant = {"office.state.write": "grant:office-state",
                 "objective.submit": "grant:objective-submit",
                 "resident.status.read": "grant:status-read",
                 "pending.website.account.session.read": "grant:test-session-boundary"}[action]
        return {"principal_id": "resident:grace", "grant_id": grant}


class _AuthorityRegistry:
    def __init__(self): self.calls = []
    def set_office_state(self, credential, office_id, state, *, expected_revision):
        self.calls.append((credential, office_id, state, expected_revision))
        return expected_revision + 1


class _Pipeline:
    def __init__(self): self.calls = []
    def submit_objective(self, objective_id, request, criteria, **kwargs):
        self.calls.append((objective_id, request, criteria, kwargs))
        return {"objective_id": objective_id, "status": "RECEIVED"}


class _Projection:
    def __init__(self): self.calls = 0
    def status(self):
        self.calls += 1
        return {"projection_status": "healthy", "assignments_total": 0}


class _State:
    def __init__(self):
        self.catalog = [{
            "capability_id": "resident.office.state.write",
            "description": "Update the Grace office state",
            "authority_action": "office.state.write",
            "owner_office": "office:grace",
            "implementation_ref": "AuthorityRegistry.set_office_state.v1",
            "dependencies": [], "resources": [], "enabled": True,
            "authorization_contract": {"mode": "exact_grant",
                "action": "office.state.write", "scope_policy": "exact_scope"},
            "input_schema": {"type": "object", "additionalProperties": False,
                "required": ["expected_revision", "state"],
                "properties": {"expected_revision": {"type": "integer", "minimum": 1},
                               "state": {"type": "object"}}},
        }]
        self.grants = [("resident:grace", "office.state.write", "office:office:grace")]


class _Provider:
    def __init__(self, answers):
        self.model = "test-80b"
        self.model_sha256 = "a" * 64
        self.provider_id = "test.reasoning"
        self.answers = list(answers)
        self.calls = []
    def readiness(self): return ProviderReadiness("READY", self.model, "ready")
    def complete_chat(self, messages, *, max_tokens, expected_revision, timeout_seconds=120):
        self.calls.append(messages)
        return ChatCompletion(self.answers.pop(0), self.model, 10, 8, "stop",
                              provider_id=self.provider_id)


class GraceCapabilityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.state = _State()
        self.authority = _AuthorityRegistry()
        self.pipeline = _Pipeline()
        self.registry = GraceCapabilityRegistry(
            dsn="postgresql://test", resident_credential="r" * 48,
            authorizer=_Authorizer(), authority_registry=self.authority,
            pipeline=self.pipeline,
            connect=lambda: _Connection(self.state))

    def test_registered_capability_is_exposed_only_with_exact_grant_and_schema(self):
        specs = self.registry.tool_specs()
        self.assertEqual([item["name"] for item in specs], ["resident.office.state.write"])
        self.assertEqual(specs[0]["inputSchema"]["properties"]["scope_ref"]["enum"],
                         ["office:office:grace"])

    def test_authorized_invocation_uses_existing_authority_api_and_returns_result(self):
        result = self.registry.invoke("resident.office.state.write", {
            "scope_ref": "office:office:grace",
            "input": {"expected_revision": 4, "state": {"mode": "unchanged"}},
        })
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["authorization"]["principal_id"], "resident:grace")
        self.assertEqual(result["result"]["revision"], 5)
        self.assertEqual(result["call"]["arguments"]["scope_ref"], "office:office:grace")
        self.assertEqual(len(result["call"]["input_sha256"]), 64)
        self.assertEqual(len(self.authority.calls), 1)

    def test_denied_exact_scope_does_not_reach_executor(self):
        result = self.registry.invoke("resident.office.state.write", {
            "scope_ref": "office:office:other",
            "input": {"expected_revision": 4, "state": {"mode": "unchanged"}},
        })
        self.assertEqual(result["error"]["code"], "capability_not_authorized")
        self.assertEqual(result["call"]["arguments"]["scope_ref"], "office:office:other")
        self.assertEqual(self.authority.calls, [])

    def test_status_projection_is_exposed_only_with_exact_read_grant(self):
        self.state.catalog.append({
            "capability_id": "resident.status.read",
            "description": "Read bounded institutional status projections",
            "authority_action": "resident.status.read", "owner_office": "office:grace",
            "implementation_ref": "dashboard.projection.v1", "dependencies": [],
            "resources": [{"resource_id": "institution:riverview"}], "enabled": True,
            "authorization_contract": {"mode": "exact_grant",
                "action": "resident.status.read", "scope_policy": "exact_scope"},
            "input_schema": {"type": "object", "additionalProperties": False,
                              "required": [], "properties": {}},
        })
        projection = _Projection()
        registry = GraceCapabilityRegistry(
            dsn="postgresql://test", resident_credential="r" * 48,
            authorizer=_Authorizer(), authority_registry=self.authority,
            dashboard_projection=projection, connect=lambda: _Connection(self.state))
        self.assertNotIn("resident.status.read", {tool["name"] for tool in registry.tool_specs()})
        denied = registry.invoke("resident.status.read", {
            "scope_ref": "institution:riverview", "input": {}})
        self.assertEqual(denied["error"]["code"], "capability_not_authorized")
        self.assertEqual(projection.calls, 0)

        self.state.grants.append(("resident:grace", "resident.status.read",
                                  "institution:riverview"))
        self.assertIn("resident.status.read", {tool["name"] for tool in registry.tool_specs()})
        result = registry.invoke("resident.status.read", {
            "scope_ref": "institution:riverview", "input": {}})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["authorization"]["scope_ref"], "institution:riverview")
        self.assertEqual(result["result"]["projection_status"], "healthy")
        self.assertEqual(projection.calls, 1)

    def test_engineering_submission_uses_existing_pipeline_and_waits_for_verifier(self):
        self.state.catalog.append({
            "capability_id": "engineering.work_order.submit",
            "description": "Submit an authorized Engineering objective",
            "authority_action": "objective.submit", "owner_office": "office:grace",
            "implementation_ref": "grace.execution-pipeline.v1",
            "dependencies": [], "resources": [], "enabled": True,
            "authorization_contract": {"mode": "exact_grant",
                "action": "objective.submit", "scope_policy": "exact_scope"},
            "input_schema": {"type": "object", "additionalProperties": False,
                "required": ["objective_id", "request", "acceptance_criteria"],
                "properties": {"objective_id": {"type": "string"},
                    "request": {"type": "string"},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}}}},
        })
        self.state.grants.append(("resident:grace", "objective.submit", "work-order:engineering"))
        result = self.registry.invoke("engineering.work_order.submit", {
            "scope_ref": "work-order:engineering",
            "input": {"objective_id": "objective:test-1", "request": "bounded request",
                      "acceptance_criteria": ["acceptance check"]},
        })
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["result"]["objective"]["status"], "RECEIVED")
        self.assertEqual(result["result"]["verification"]["status"], "pending")
        self.assertEqual(self.pipeline.calls[0][3]["scope_ref"], "work-order:engineering")

    def test_new_registry_record_becomes_discoverable_without_prompt_change(self):
        tools = GraceInternalTools(backend=type("Backend", (), {
            "supported_tools": frozenset(), "call": lambda *_: None})(),
            capability_registry=self.registry)
        self.assertIn("resident.office.state.write", {item["name"] for item in tools.catalog()})
        self.state.catalog.append({
            "capability_id": "example.new.v1", "description": "Newly registered",
            "authority_action": "example.use", "owner_office": "office:grace",
            "implementation_ref": "uninstalled.adapter.v1", "dependencies": [],
            "resources": [], "enabled": True, "input_schema": None,
            "authorization_contract": {"mode": "exact_grant",
                "action": "example.use", "scope_policy": "exact_scope"},
            "registration_blocker": "executor_not_installed",
        })
        result = tools.call("riverview_capability_discover", {})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["call"]["arguments"], {})
        self.assertEqual(len(result["call"]["input_sha256"]), 64)
        ids = {item["capability_id"] for item in result["result"]["capabilities"]}
        self.assertEqual(ids, {"resident.office.state.write", "example.new.v1"})
        new_entry = next(item for item in result["result"]["capabilities"]
                         if item["capability_id"] == "example.new.v1")
        self.assertEqual(new_entry["authorization_status"], "not_authorized")
        self.assertFalse(new_entry["invocable"])
        self.assertEqual(new_entry["registration_blocker"], "executor_not_installed")

    def test_unsupported_authorization_contract_is_visible_and_never_selectable(self):
        self.state.catalog.append({
            "capability_id": "website.account.session.read",
            "description": "Read an authenticated Steward account session",
            "authority_action": "pending.website.account.session.read",
            "owner_office": "office:steward",
            "implementation_ref": "dashboard.account-session.v1",
            "dependencies": [], "resources": [], "enabled": False,
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "authorization_contract": {"mode": "authenticated_account_session",
                "reason": "requires caller browser session"},
            "registration_blocker": "executor_and_session_authorization_not_supported",
        })
        snapshot = self.registry.snapshot()
        item = next(row for row in snapshot["capabilities"]
                    if row["capability_id"] == "website.account.session.read")
        self.assertEqual(item["authorization_contract"]["mode"],
                         "authenticated_account_session")
        self.assertEqual(item["invocation_blocker"],
                         "executor_and_session_authorization_not_supported")
        self.assertNotIn(item["capability_id"],
                         {tool["name"] for tool in self.registry.tool_specs()})
        self.state.grants.append(("resident:grace",
            "pending.website.account.session.read", "institution:riverview"))
        result = self.registry.invoke(item["capability_id"], {
            "scope_ref": "institution:riverview", "input": {}})
        self.assertEqual(result["error"]["code"], "capability_registration_blocked")

    def test_dynamic_capability_name_is_selected_from_current_registry(self):
        selected = GraceModelRouter._required_internal_tool(
            [{"role": "user", "content": "Invoke resident.office.state.write."}],
            self.registry.tool_specs())
        self.assertEqual(selected, "resident.office.state.write")

    def test_router_discovers_live_rows_before_answering_registry_question(self):
        tool_call = ('<rv-tool-call>{"name":"riverview_capability_discover",'
                     '"arguments":{}}</rv-tool-call>')
        provider = _Provider([tool_call, "The registry result lists resident.office.state.write."])
        tools = GraceInternalTools(backend=type("Backend", (), {
            "supported_tools": frozenset(), "call": lambda *_: None})(),
            capability_registry=self.registry)
        router = GraceModelRouter(autonomic=provider, vision=provider,
            reasoning=provider, internal_tools=tools)
        completion = router.complete_chat(
            [{"role": "user", "content": "Which capabilities are registered?"}],
            max_tokens=128, expected_revision=router.model_sha256,
            required_capability="grace.reasoning.80b")
        self.assertEqual(completion.internal_tool_results[0]["tool"],
                         "riverview_capability_discover")
        actual_ids = {item["capability_id"] for item in
                      completion.internal_tool_results[0]["result"]["capabilities"]}
        self.assertEqual(actual_ids, {"resident.office.state.write"})
        followup = " ".join(item["content"] for item in provider.calls[1])
        self.assertIn("resident.office.state.write", followup)
        self.assertIn("Never infer an identifier", followup)

    def test_natural_language_capability_query_selects_live_discovery_tool(self):
        selected = GraceModelRouter._required_internal_tool(
            [{"role": "user", "content": "Which capabilities are registered?"}],
            [{"name": "riverview_capability_discover", "inputSchema": {}}])
        self.assertEqual(selected, "riverview_capability_discover")

    def test_explicit_proposal_submission_selects_registered_authorized_capability(self):
        catalog = [{"name": "proposal.draft.submit", "inputSchema": {}}]
        selected = GraceModelRouter._required_internal_tool(
            [{"role": "user", "content": "Prepare and submit a proposal for the website clock."}],
            catalog)
        self.assertEqual(selected, "proposal.draft.submit")

    def test_proposal_submission_tool_is_not_selected_when_user_withholds_submission(self):
        catalog = [{"name": "proposal.draft.submit", "inputSchema": {}}]
        selected = GraceModelRouter._required_internal_tool(
            [{"role": "user", "content": "Prepare a proposal draft, but do not submit it."}],
            catalog)
        self.assertIsNone(selected)

    def test_proposal_status_lookup_selects_exact_registered_capability(self):
        catalog = [{"name": "proposal.status.read", "inputSchema": {}}]
        selected = GraceModelRouter._required_internal_tool(
            [{"role": "user", "content": "Read proposal:00000000-0000-0000-0000-000000000000 status."}],
            catalog)
        self.assertEqual(selected, "proposal.status.read")

    def test_proposal_request_forces_model_tool_call_and_records_result(self):
        class Tools:
            def __init__(self): self.calls = []
            def catalog(self):
                return [{"name": "proposal.draft.submit",
                         "inputSchema": {"type": "object", "required": ["content"]}}]
            def call(self, name, arguments):
                self.calls.append((name, arguments))
                return {"status": "ok", "tool": name,
                        "result": {"proposal_id": "proposal:00000000-0000-0000-0000-000000000000",
                                   "revision": 1, "lifecycle_status": "DRAFT",
                                   "readback_verified": True}}

        provider = _Provider([
            '<rv-tool-call>{"name":"proposal.draft.submit","arguments":{"content":{}}}</rv-tool-call>',
            "The draft was persisted and is awaiting Steward approval.",
        ])
        tools = Tools()
        router = GraceModelRouter(autonomic=provider, vision=provider,
            reasoning=provider, internal_tools=tools)
        result = router.complete_chat(
            [{"role": "user", "content": "Prepare and submit a proposal for a date/time clock."}],
            max_tokens=128, expected_revision=router.model_sha256,
            required_capability="grace.reasoning.80b")
        self.assertEqual([name for name, _ in tools.calls], ["proposal.draft.submit"])
        self.assertEqual(result.internal_tool_results[0]["result"]["lifecycle_status"], "DRAFT")
        self.assertIn("proposal.draft.submit", provider.calls[0][0]["content"])
        self.assertIn("do not approve, promote, dispatch, or implement it",
                      provider.calls[0][0]["content"].lower())
        self.assertTrue(any('"proposal_id":"proposal:00000000-0000-0000-0000-000000000000"'
                            in message.get("content", "")
                            for call in provider.calls for message in call))

    def test_proposal_status_executor_returns_bounded_receipt_for_author(self):
        class Proposals:
            def get(self, _proposal_id):
                return {"proposal": {"proposal_id": "proposal:00000000-0000-0000-0000-000000000000",
                    "created_by": "resident:grace", "lifecycle_status": "DRAFT"},
                    "revision": {"revision": 1, "content_sha256": "a" * 64,
                                 "title": "clock"}}

        self.registry.proposal_registry = Proposals()
        receipt = self.registry._read_proposal_status(
            scope_ref="institution:proposal-drafts",
            inputs={"proposal_id": "proposal:00000000-0000-0000-0000-000000000000"},
            credential="r" * 48,
            grant={"principal_id": "resident:grace"})
        self.assertEqual(receipt, {
            "proposal_id": "proposal:00000000-0000-0000-0000-000000000000",
            "revision": 1, "content_sha256": "a" * 64,
            "author_principal_id": "resident:grace", "lifecycle_status": "DRAFT",
            "approval": "awaiting_steward_decision", "readback_verified": True})
        self.assertNotIn("title", receipt)

    def test_proposal_status_executor_does_not_disclose_another_authors_record(self):
        class Proposals:
            def get(self, _proposal_id):
                return {"proposal": {"proposal_id": "proposal:00000000-0000-0000-0000-000000000000",
                    "created_by": "resident:other", "lifecycle_status": "DRAFT"},
                    "revision": {"revision": 1, "content_sha256": "a" * 64}}

        self.registry.proposal_registry = Proposals()
        with self.assertRaisesRegex(PermissionError, "proposal_not_found"):
            self.registry._read_proposal_status(
                scope_ref="institution:proposal-drafts",
                inputs={"proposal_id": "proposal:00000000-0000-0000-0000-000000000000"},
                credential="r" * 48, grant={"principal_id": "resident:grace"})


if __name__ == "__main__":
    unittest.main()

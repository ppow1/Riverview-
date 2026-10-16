# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_resident_reasoning.py
# Component: RESIDENT-REASONING
# Revision: 1.0.15
# Purpose: Verify resident regrounding, bounded provider routing and durable resume
# Execution Model: Isolated PostgreSQL authority registry integration tests
# Observability: Assertions inspect persisted office state and provider outcomes
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; Psycopg 3
# Authority: Creates and drops only unique disposable schemas
# Contracts: docs/components/RESIDENT_REASONING.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# Changed: 2026-10-11 UTC | RV-M4.2-001 | Correct exact office-state grant scope and exercise configured timeout failover
# Changed: 2026-10-11 UTC | RV-M4.2-TEST-FIXTURE | Keep default VERIFIED fake outcomes reusable across runtime reconstruction
# Changed: 2026-10-11 UTC | RV-M4.2-FAKE-PROVIDER-IMPORT-FIX | Import test status enum in the fake provider call path
# Changed: 2026-10-11 UTC | RV-M4.2-REDACTION-AND-CONTEXT-RACE-TESTS | Verify credential keys are withheld and changed assignment context is not committed
# Changed: 2026-10-11 UTC | RV-M4.2-AUTHORITY-DENIAL-STATUS | Verify revoked exact office-state grant prevents provider invocation
# Changed: 2026-10-11 UTC | RV-M4.2-ENFORCE-PER-ROUTE-TOKEN-BUDGET | Verify a provider cannot exceed its allocated share before planning is persisted
# Changed: 2026-10-11 UTC | RV-M4.2-COMPLETE-ROUTE-TEST | Configure the explicit fallback target in the token-budget boundary test
# Changed: 2026-10-11 UTC | RV-M4.2-ROUTE-MINIMUM-BUDGET | Verify too-small total budget rejects the route before provider invocation
# Changed: 2026-10-11 UTC | RV-M4.4-CONTEXT-FAILURE-CLASS | Verify oversized evidence and unserializable evidence have distinct outcomes
# Changed: 2026-10-11 UTC | RV-M4.1-M4.2-OCCUPANT-REPLACEMENT-INTEGRATION | Verify a replacement Grace occupant resumes office-keyed reasoning state under its own exact grant
# Changed: 2026-10-11 UTC | RV-M4.1-PERSISTENT-RUNTIME-INTEGRATION | Exercise office-bound reasoning through the persistent execution service across replacement
# Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-TIMEOUT-001 | Verify sixty-second provider deadlines remain bounded
# Changed: 2026-10-15 UTC | RV-GRACE-AUTHORIZED-SNAPSHOT-001 | Revalidate through authorized function when direct snapshot SELECT is denied
# Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Verify external advice is separate from verified knowledge
# =============================================================================

import hashlib
import os
import secrets
import time
import unittest
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


class _Assignments:
    def __init__(self):
        self.current = {"id": "assignment:reasoning-test", "revision": "7",
                        "state": "in_progress", "workflow_stage": "design",
                        "acceptance_criteria": ["produce a test plan"]}

    def read(self, assignment_id):
        if assignment_id != self.current["id"]:
            raise KeyError("unknown assignment")
        return dict(self.current)


class _Knowledge:
    def __init__(self, statuses=None):
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
        self.statuses = list(statuses) if statuses is not None else []
        self.calls = []

    def _result(self, operation, *args):
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
        self.calls.append((operation, args))
        status = self.statuses.pop(0) if self.statuses else KnowledgeStatus.VERIFIED
        if status.value == "VERIFIED":
            return KnowledgeResult(status, {"rule": "follow the active contract"},
                                   ("repo://docs/architecture/CORE_CONTRACT.md",),
                                   "1.0.1", "a" * 64, True)
        return KnowledgeResult(status)

    def ground_assignment(self, assignment):
        return self._result("ground", assignment)

    def reground_assignment(self, assignment, trigger):
        return self._result("reground", assignment, trigger)

    def preflight_action(self, assignment, action):
        return self._result("preflight", assignment, action)

    def record_learning(self, assignment, outcome):
        return self._result("learning", assignment, outcome)


class _Provider:
    def __init__(self, provider_id, *, fail=False, delay=0, summary="plan"):
        self.provider_id = provider_id
        self.fail = fail
        self.delay = delay
        self.summary = summary
        self.requests = []

    def propose(self, request):
        from riverview_core.resident_reasoning import PlanProposal, PlanStep
        self.requests.append(request)
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("provider unavailable")
        return PlanProposal(self.summary,
                            (PlanStep("step-1", "develop work", ("test result exists",)),), 17)


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class ResidentReasoningTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.institutional_authority import AuthorityRegistry
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        migrations = Path(__file__).resolve().parents[1] / "src/riverview_core/institutional_authority/migrations"
        apply_migrations(DSN, schema=self.schema, migrations_dir=migrations)
        self.registry = AuthorityRegistry(DSN, schema=self.schema)
        self.steward_token = secrets.token_urlsafe(32)
        self.steward_id = "steward:" + uuid4().hex
        with self.admin.cursor() as cur:
            cur.execute(f"INSERT INTO {self.schema}.institutional_principals(principal_id,principal_kind) VALUES (%s,'steward')",
                        (self.steward_id,))
            cur.execute(f"INSERT INTO {self.schema}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)",
                        (uuid4(), self.steward_id, hashlib.sha256(self.steward_token.encode()).digest()))
            for action in ("authority.grant", "identity.manage", "office.manage"):
                cur.execute(f"INSERT INTO {self.schema}.authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) VALUES (%s,%s,%s,'institution',%s,'rv.policy:test.v1')",
                            ("bootstrap:" + action + ":" + uuid4().hex, self.steward_id, action, self.steward_id))
        self.office_id = "office:" + uuid4().hex
        self.registry.create_office(self.steward_token, self.office_id, "engineering director")
        self.principal_id = "resident:" + uuid4().hex
        self.resident_token = self.registry.create_principal(
            self.steward_token, self.principal_id, "resident", office_id=self.office_id)
        self.occupant_id = "occupant:" + uuid4().hex
        self.registry.create_occupant(self.steward_token, self.occupant_id,
                                      principal_id=self.principal_id)
        self.impl_a = "implementation:" + uuid4().hex
        self.impl_b = "implementation:" + uuid4().hex
        self.registry.create_implementation(self.steward_token, self.impl_a, kind="model",
                                            provider_ref="provider.a", revision="model-rev-a")
        self.registry.create_implementation(self.steward_token, self.impl_b, kind="model",
                                            provider_ref="provider.b", revision="model-rev-b")
        self.registry.bind_office(self.steward_token, self.office_id, self.occupant_id, self.impl_a)
        self.state_grant = "grant:" + uuid4().hex
        self.registry.grant(self.steward_token, self.principal_id, "office.state.write",
                            "office:" + self.office_id, grant_id=self.state_grant,
                            policy_ref="rv.policy:resident-runtime.v1")
        self.assignments = _Assignments()
        self.knowledge = _Knowledge()

    def tearDown(self):
        from psycopg import sql
        self.registry.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def _runtime(self, providers, *, fallbacks=None, knowledge=None, timeout=0.1):
        from riverview_core.resident_reasoning import ResidentReasoner
        return ResidentReasoner(registry=self.registry, office_id=self.office_id,
                                resident_credential=self.resident_token,
                                assignments=self.assignments,
                                knowledge=knowledge or self.knowledge,
                                providers=providers, fallback_routes=fallbacks,
                                timeout_seconds=timeout)

    def test_provider_deadline_accepts_sixty_seconds_and_remains_bounded(self):
        runtime = self._runtime({"provider.a": _Provider("provider.a")}, timeout=60)
        self.assertEqual(runtime.timeout_seconds, 60)
        with self.assertRaises(ValueError):
            self._runtime({"provider.a": _Provider("provider.a")}, timeout=60.1)

    def test_proposal_uses_runtime_office_function_when_authority_tables_are_restricted(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.errors import InsufficientPrivilege
        from riverview_core.institutional_authority import AuthorityRegistry, RegistryUnavailable
        from riverview_core.resident_reasoning import ReasoningStatus

        identity = self.admin.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()
        if not identity[0]:
            self.skipTest("isolated PostgreSQL test DSN needs temporary-role authority")
        runtime_role = "rvtest_reasoner_" + uuid4().hex[:20]
        runtime_password = secrets.token_urlsafe(32)
        runtime_registry = None
        try:
            self.admin.execute(sql.SQL(
                "CREATE ROLE {} LOGIN NOINHERIT PASSWORD {} NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOBYPASSRLS").format(
                    sql.Identifier(runtime_role), sql.Literal(runtime_password)))
            self.admin.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(self.schema), sql.Identifier(runtime_role)))
            self.admin.execute(sql.SQL(
                "GRANT EXECUTE ON FUNCTION {}.read_authorized_office_state(bytea,text) TO {}"
            ).format(sql.Identifier(self.schema), sql.Identifier(runtime_role)))
            self.admin.execute(sql.SQL(
                "GRANT EXECUTE ON FUNCTION {}.write_authorized_office_state(bytea,text,jsonb,bigint) TO {}"
            ).format(sql.Identifier(self.schema), sql.Identifier(runtime_role)))
            runtime_dsn = make_conninfo(DSN, user=runtime_role, password=runtime_password)
            runtime_registry = AuthorityRegistry(runtime_dsn, schema=self.schema, runtime_safe=True)
            with psycopg.connect(runtime_dsn) as restricted:
                with self.assertRaises(InsufficientPrivilege):
                    restricted.execute(
                        sql.SQL("SELECT * FROM {}.office_bindings LIMIT 1").format(
                            sql.Identifier(self.schema))).fetchone()

            provider = _Provider("provider.a", summary="authorized snapshot proposal")
            reasoner = self._runtime({"provider.a": provider}, timeout=1)
            reasoner.registry = runtime_registry
            reasoner._credential = self.resident_token
            result = reasoner.propose(
                self.assignments.current["id"], trigger="restricted_runtime_role",
                token_budget=100)
            self.assertEqual(result.status, ReasoningStatus.PROPOSED)
            self.assertEqual(len(provider.requests), 1)
            persisted = self.registry.office_snapshot(self.office_id)["state"][
                "resident_reasoning_v1"]["plans"][self.assignments.current["id"]]
            self.assertEqual(persisted["summary"], "authorized snapshot proposal")
            with self.assertRaises(RegistryUnavailable):
                runtime_registry.office_snapshot(self.office_id)
        finally:
            if runtime_registry is not None:
                runtime_registry.close()
            self.admin.execute(sql.SQL("REVOKE USAGE ON SCHEMA {} FROM {}").format(
                sql.Identifier(self.schema), sql.Identifier(runtime_role)))
            self.admin.execute(sql.SQL(
                "REVOKE EXECUTE ON FUNCTION {}.read_authorized_office_state(bytea,text) FROM {}"
            ).format(sql.Identifier(self.schema), sql.Identifier(runtime_role)))
            self.admin.execute(sql.SQL(
                "REVOKE EXECUTE ON FUNCTION {}.write_authorized_office_state(bytea,text,jsonb,bigint) FROM {}"
            ).format(sql.Identifier(self.schema), sql.Identifier(runtime_role)))
            self.admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(
                sql.Identifier(runtime_role)))

    def test_plan_and_grounding_are_durable_across_runtime_replacement(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        provider = _Provider("provider.a", summary="plan one")
        first = self._runtime({"provider.a": provider}).propose(
            self.assignments.current["id"], trigger="resident_restore", token_budget=100)
        self.assertEqual(first.status, ReasoningStatus.PROPOSED)
        snapshot = self.registry.office_snapshot(self.office_id)
        stored = snapshot["state"]["resident_reasoning_v1"]
        self.assertEqual(stored["plans"][self.assignments.current["id"]]["summary"], "plan one")
        self.assertEqual([x["grounding"]["status"] for x in stored["outcomes"]], ["VERIFIED"])
        self.assertEqual(stored["outcomes"][-1]["regrounding"]["source_revision"], "1.0.1")
        replacement_provider = _Provider("provider.a", summary="resumed plan")
        second = self._runtime({"provider.a": replacement_provider}).propose(
            self.assignments.current["id"], trigger="context_compaction", token_budget=100)
        self.assertEqual(second.status, ReasoningStatus.PROPOSED)
        self.assertEqual(replacement_provider.requests[0].prior_plan["summary"], "plan one")
        self.assertNotIn("credential", replacement_provider.requests[0].__dataclass_fields__)

    def test_external_advisory_reaches_reasoning_separately_from_verified_knowledge(self):
        import json
        from riverview_core.resident_reasoning import ReasoningStatus

        provider = _Provider("provider.a", summary="evaluate advice")
        reasoner = self._runtime({"provider.a": provider})
        advisory = {
            "schema_version": "rv.external-reasoning.response.v1",
            "request_id": str(uuid4()), "correlation_id": str(uuid4()),
            "response_id": "advisory-test-1",
            "advisory": "Consider the alternative implementation path.",
            "evidence_references": ["test://external-evidence"],
            "provider_id": "external.test", "provider_model": "advisory-model-v1",
        }
        result = reasoner.propose(self.assignments.current["id"],
            trigger="external_reasoning_resume", token_budget=100,
            external_advisory=advisory)
        self.assertEqual(result.status, ReasoningStatus.PROPOSED)
        request = provider.requests[0]
        self.assertEqual(request.external_advisory, advisory)
        self.assertEqual(request.verified_knowledge[0]["status"], "VERIFIED")
        self.assertNotIn(advisory["advisory"], json.dumps(request.verified_knowledge))
        state = self.registry.office_snapshot(self.office_id)["state"][reasoner.STATE_KEY]
        metadata = state["outcomes"][-1]["external_advisory"]
        self.assertEqual(metadata["request_id"], advisory["request_id"])
        self.assertEqual(metadata["provider_model"], advisory["provider_model"])
        self.assertEqual(state["plans"][self.assignments.current["id"]]["summary"],
                         "evaluate advice")

    def test_malformed_external_advisory_fails_before_provider_call(self):
        provider = _Provider("provider.a")
        reasoner = self._runtime({"provider.a": provider})
        with self.assertRaises(ValueError):
            reasoner.propose(self.assignments.current["id"],
                trigger="external_reasoning_resume", token_budget=100,
                external_advisory={"advisory": "untyped"})
        self.assertEqual(provider.requests, [])

    def test_replacement_occupant_resumes_reasoning_with_new_binding_and_grant(self):
        """Office state follows the role while authority follows the occupant."""
        from riverview_core.institutional_authority import AuthorityDenied
        from riverview_core.resident_reasoning import ReasoningStatus, ResidentReasoner

        first_provider = _Provider("provider.a", summary="plan before replacement")
        first = self._runtime({"provider.a": first_provider}).propose(
            self.assignments.current["id"], trigger="initial", token_budget=100)
        self.assertEqual(first.status, ReasoningStatus.PROPOSED)

        replacement_principal = "resident:" + uuid4().hex
        replacement_token = self.registry.create_principal(
            self.steward_token, replacement_principal, "resident", office_id=self.office_id)
        replacement_occupant = "occupant:" + uuid4().hex
        self.registry.create_occupant(self.steward_token, replacement_occupant,
                                      principal_id=replacement_principal)
        self.registry.bind_office(self.steward_token, self.office_id,
                                  replacement_occupant, self.impl_b)
        self.registry.grant(self.steward_token, replacement_principal,
                            "office.state.write", "office:" + self.office_id,
                            policy_ref="rv.policy:resident-runtime.v1")

        replacement_provider = _Provider("provider.b", summary="continued plan")
        replacement_runtime = ResidentReasoner(
            registry=self.registry, office_id=self.office_id,
            resident_credential=replacement_token, assignments=self.assignments,
            knowledge=self.knowledge, providers={"provider.b": replacement_provider},
            timeout_seconds=0.1)
        resumed = replacement_runtime.propose(
            self.assignments.current["id"], trigger="occupant_replacement", token_budget=100)

        self.assertEqual(resumed.status, ReasoningStatus.PROPOSED)
        request = replacement_provider.requests[0]
        self.assertEqual(request.binding_revision, 2)
        self.assertEqual(request.implementation_revision, "model-rev-b")
        self.assertEqual(request.prior_plan["summary"], "plan before replacement")
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize(self.resident_token, "office.state.write",
                                    "office:" + self.office_id)

        # Even an erroneous later re-grant cannot make a former occupant current.
        self.registry.grant(self.steward_token, self.principal_id,
                            "office.state.write", "office:" + self.office_id,
                            policy_ref="rv.policy:resident-runtime.v1")
        snapshot = self.registry.office_snapshot(self.office_id)
        self.assertEqual(snapshot["state"]["resident_reasoning_v1"]["plans"]
                         [self.assignments.current["id"]]["summary"], "continued plan")

    def test_persistent_service_rehydrates_office_reasoning_after_occupant_replacement(self):
        """A reconstructed service uses current occupant authority and office-keyed plan."""
        from riverview_core.resident_execution.service import GraceExecutionService
        from riverview_core.institutional_authority import AuthorityDenied
        from riverview_core.resident_reasoning import ResidentReasoner

        class Pipeline:
            authority_ref = "work-order:test"

            def __init__(self, assignment_id):
                self.assignment_id = assignment_id
                self.proposals = []

            def grounded_objectives(self, *, scope_ref, limit=25, objective_id=None):
                if scope_ref != self.authority_ref:
                    return []
                if objective_id and objective_id != self.assignment_id:
                    return []
                return [{"objective_id": self.assignment_id, "revision": 1}]

            def record_proposal(self, objective_id, proposal, *, actor_id):
                self.proposals.append((objective_id, proposal, actor_id))

        pipeline = Pipeline(self.assignments.current["id"])
        first_provider = _Provider("provider.a", summary="service plan before replacement")
        first_reasoner = self._runtime({"provider.a": first_provider})
        first_service = GraceExecutionService(
            pipeline, None, None, dispatch_credential="dispatch",
            authority_ref=pipeline.authority_ref, verifier_id="verifier",
            verifier_credential="verify", artifact_root="/tmp/unused",
            resident_reasoner=first_reasoner)
        self.assertTrue(first_service.reason_one_grounded_objective())
        self.assertEqual(pipeline.proposals[0][2], "office:" + self.office_id)

        replacement_principal = "resident:" + uuid4().hex
        replacement_token = self.registry.create_principal(
            self.steward_token, replacement_principal, "resident", office_id=self.office_id)
        replacement_occupant = "occupant:" + uuid4().hex
        self.registry.create_occupant(self.steward_token, replacement_occupant,
                                      principal_id=replacement_principal)
        self.registry.bind_office(self.steward_token, self.office_id,
                                  replacement_occupant, self.impl_b)
        self.registry.grant(self.steward_token, replacement_principal,
                            "office.state.write", "office:" + self.office_id,
                            policy_ref="rv.policy:resident-runtime.v1")
        replacement_provider = _Provider("provider.b", summary="service plan after replacement")
        replacement_reasoner = ResidentReasoner(
            registry=self.registry, office_id=self.office_id,
            resident_credential=replacement_token, assignments=self.assignments,
            knowledge=self.knowledge, providers={"provider.b": replacement_provider},
            timeout_seconds=0.1)
        restarted_service = GraceExecutionService(
            pipeline, None, None, dispatch_credential="dispatch",
            authority_ref=pipeline.authority_ref, verifier_id="verifier",
            verifier_credential="verify", artifact_root="/tmp/unused",
            resident_reasoner=replacement_reasoner)
        self.assertTrue(restarted_service.reason_one_grounded_objective())
        self.assertEqual(replacement_provider.requests[0].binding_revision, 2)
        self.assertEqual(replacement_provider.requests[0].prior_plan["summary"],
                         "service plan before replacement")
        self.assertEqual(pipeline.proposals[-1][1].summary, "service plan after replacement")
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize(self.resident_token, "office.state.write",
                                    "office:" + self.office_id)

        stale_service = GraceExecutionService(
            pipeline, None, None, dispatch_credential="dispatch",
            authority_ref=pipeline.authority_ref, verifier_id="verifier",
            verifier_credential="verify", artifact_root="/tmp/unused",
            resident_reasoner=first_reasoner)
        self.assertFalse(stale_service.reason_one_grounded_objective())
        self.assertEqual(len(pipeline.proposals), 2)
        self.assertEqual(len(first_provider.requests), 1)
        with self.assertRaises(AuthorityDenied):
            self.registry.set_office_state(self.resident_token, self.office_id,
                                            {"unauthorized": True})
        durable = self.registry.office_snapshot(self.office_id)["state"]["resident_reasoning_v1"]
        self.assertEqual(durable["plans"][self.assignments.current["id"]]["summary"],
                         "service plan after replacement")

    def test_unverified_grounding_waits_and_is_persisted(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        from riverview_core.worker_adapter.knowledge import KnowledgeStatus
        knowledge = _Knowledge([KnowledgeStatus.UNAVAILABLE, KnowledgeStatus.VERIFIED])
        provider = _Provider("provider.a")
        result = self._runtime({"provider.a": provider}, knowledge=knowledge).propose(
            self.assignments.current["id"], trigger="before_reasoning", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.WAITING_FOR_EVIDENCE)
        self.assertEqual(provider.requests, [])
        snapshot = self.registry.office_snapshot(self.office_id)
        event = snapshot["state"]["resident_reasoning_v1"]["outcomes"][-1]
        self.assertEqual(event["grounding"]["status"], "UNAVAILABLE")
        self.assertEqual(event["status"], "WAITING_FOR_EVIDENCE")

    def test_only_explicit_timeout_fallback_is_used(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        slow = _Provider("provider.a", delay=0.15)
        backup = _Provider("provider.b", summary="fallback proposal")
        result = self._runtime({"provider.a": slow, "provider.b": backup},
                               fallbacks={"provider.a": ("provider.b",)}).propose(
            self.assignments.current["id"], trigger="provider_failure", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.PROPOSED)
        self.assertEqual(result.provider_id, "provider.b")
        self.assertEqual(result.proposal.summary, "fallback proposal")
        self.assertEqual(slow.requests[0].token_budget, 50)
        self.assertEqual(backup.requests[0].token_budget, 50)

    def test_provider_replacement_does_not_change_assignment_authority(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        before = self.admin.execute(
            f"SELECT principal_id,action,scope_ref,revoked_at FROM {self.schema}.authority_grants ORDER BY principal_id,action,scope_ref"
        ).fetchall()
        self.registry.bind_office(self.steward_token, self.office_id, self.occupant_id, self.impl_b)
        provider = _Provider("provider.b", summary="new implementation")
        result = self._runtime({"provider.b": provider}).propose(
            self.assignments.current["id"], trigger="implementation_replacement", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.PROPOSED)
        self.assertEqual(provider.requests[0].implementation_revision, "model-rev-b")
        after = self.admin.execute(
            f"SELECT principal_id,action,scope_ref,revoked_at FROM {self.schema}.authority_grants ORDER BY principal_id,action,scope_ref"
        ).fetchall()
        self.assertEqual(before, after)

    def test_unlisted_provider_is_unavailable_not_an_implicit_fallback(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        result = self._runtime({}).propose(
            self.assignments.current["id"], trigger="before_reasoning", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.UNAVAILABLE)
        self.assertEqual(result.detail_code, "PROVIDER_ROUTE_UNAVAILABLE")

    def test_credential_shaped_assignment_fields_never_reach_provider(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        provider = _Provider("provider.a")
        self.assignments.current["access_token"] = "never-forward-this"
        result = self._runtime({"provider.a": provider}).propose(
            self.assignments.current["id"], trigger="before_reasoning", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.WAITING_FOR_EVIDENCE)
        self.assertEqual(result.detail_code, "ASSIGNMENT_CONTEXT_REDACTION_REJECTED")
        self.assertEqual(provider.requests, [])
        state = self.registry.office_snapshot(self.office_id)["state"]["resident_reasoning_v1"]
        self.assertEqual(state["outcomes"][-1]["grounding"]["status"], "UNAVAILABLE")

    def test_assignment_revision_change_during_reasoning_discards_proposal(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        assignments = self.assignments

        class MutatingProvider(_Provider):
            def propose(self, request):
                proposal = super().propose(request)
                assignments.current["revision"] = "8"
                return proposal

        provider = MutatingProvider("provider.a")
        result = self._runtime({"provider.a": provider}).propose(
            self.assignments.current["id"], trigger="before_reasoning", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.STALE_CONTEXT)
        runtime_state = self.registry.office_snapshot(self.office_id)["state"]["resident_reasoning_v1"]
        self.assertNotIn(self.assignments.current["id"], runtime_state.get("plans", {}))

    def test_revoked_office_state_grant_denies_before_provider_invocation(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        self.registry.revoke_grant(self.steward_token, self.state_grant)
        provider = _Provider("provider.a")
        result = self._runtime({"provider.a": provider}).propose(
            self.assignments.current["id"], trigger="before_reasoning", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.AUTHORITY_DENIED)
        self.assertEqual(result.detail_code, "OFFICE_STATE_GRANT_REQUIRED")
        self.assertEqual(provider.requests, [])

    def test_provider_output_over_attempt_token_budget_is_not_persisted(self):
        from riverview_core.resident_reasoning import PlanProposal, PlanStep, ReasoningStatus

        class OverBudgetProvider(_Provider):
            def propose(self, request):
                self.requests.append(request)
                return PlanProposal("over budget",
                                    (PlanStep("step-1", "develop work", ("test result exists",)),),
                                    request.token_budget + 1)

        provider = OverBudgetProvider("provider.a")
        result = self._runtime({"provider.a": provider, "provider.b": _Provider("provider.b")},
                               fallbacks={"provider.a": ("provider.b",)}).propose(
            self.assignments.current["id"], trigger="before_reasoning", token_budget=100)
        self.assertEqual(result.status, ReasoningStatus.INVALID_PROPOSAL)
        self.assertEqual(provider.requests[0].token_budget, 50)
        state = self.registry.office_snapshot(self.office_id)["state"]["resident_reasoning_v1"]
        self.assertNotIn(self.assignments.current["id"], state.get("plans", {}))

    def test_total_budget_smaller_than_route_is_rejected_without_provider_call(self):
        from riverview_core.resident_reasoning import ReasoningStatus
        primary = _Provider("provider.a")
        secondary = _Provider("provider.b")
        result = self._runtime({"provider.a": primary, "provider.b": secondary},
                               fallbacks={"provider.a": ("provider.b",)}).propose(
            self.assignments.current["id"], trigger="before_reasoning", token_budget=1)
        self.assertEqual(result.status, ReasoningStatus.INVALID_PROPOSAL)
        self.assertEqual(result.detail_code, "BUDGET_TOO_SMALL_FOR_ROUTE")
        self.assertEqual(primary.requests, [])
        self.assertEqual(secondary.requests, [])

    def test_oversized_and_unserializable_grounding_are_reported_distinctly(self):
        from riverview_core.resident_reasoning import ReasoningStatus, ResidentReasoner
        from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus

        class FixedKnowledge:
            def __init__(self, value):
                self.value = value
            def ground_assignment(self, assignment):
                return KnowledgeResult(KnowledgeStatus.VERIFIED, self.value,
                    ("repo://docs/evidence.md",), "a" * 40, "b" * 64, True)
            def reground_assignment(self, assignment, trigger):
                return self.ground_assignment(assignment)

        provider = _Provider("provider.a")
        too_large = {"evidence": "x" * (ResidentReasoner.MAX_CONTEXT_BYTES + 1)}
        large_result = self._runtime({"provider.a": provider},
            knowledge=FixedKnowledge(too_large)).propose(
                self.assignments.current["id"], trigger="context_test", token_budget=20)
        self.assertEqual(large_result.status, ReasoningStatus.WAITING_FOR_EVIDENCE)
        self.assertEqual(large_result.detail_code, "CONTEXT_TOO_LARGE")
        self.assertEqual(provider.requests, [])

        class NotJson:
            pass
        invalid_result = self._runtime({"provider.a": provider},
            knowledge=FixedKnowledge({"evidence": NotJson()})).propose(
                self.assignments.current["id"], trigger="serialization_test", token_budget=20)
        self.assertEqual(invalid_result.status, ReasoningStatus.WAITING_FOR_EVIDENCE)
        self.assertEqual(invalid_result.detail_code, "KNOWLEDGE_NOT_SERIALIZABLE")
        self.assertEqual(provider.requests, [])


if __name__ == "__main__":
    unittest.main()

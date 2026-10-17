# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_resident_reasoning.py
# Component: RESIDENT-REASONING
# Revision: 1.0.4
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


if __name__ == "__main__":
    unittest.main()

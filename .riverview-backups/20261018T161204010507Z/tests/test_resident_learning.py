# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_learning.py
# Component: RESIDENT-LEARNING-GOVERNANCE
# Revision: 1.0.0
# Purpose: Test learning lifecycle, scope isolation, authorization denial, correction, rollback, and resumption
# Execution Model: Isolated unit tests with in-memory test double
# Observability: Lifecycle states, events, provenance, and authorization calls
# Dependencies: Python 3.10+; resident_learning module
# Authority: Synthetic principals and local records only; no real grants or database
# Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-IMPLEMENTATION-001 | Add lifecycle service tests
# Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
import copy
import unittest
from uuid import uuid4

from riverview_core.resident_execution.resident_learning import (
    AuthorizationDenied, LearningConflict, LearningValidationError,
    ResidentLearningService,
)

NOW = "2026-10-18T15:00:00Z"
EVIDENCE = [{"source_ref":"conversation://fixture/1", "source_kind":"resident_statement",
    "captured_at":NOW, "source_revision":None, "source_sha256":None}]
PROVENANCE = {"recorder_id":"resident:grace", "method":"explicit save",
    "implementation_revision":None, "interpretation":"resident_assertion"}


class FakeAuthorizer:
    def __init__(self):
        self.denied = set()
        self.calls = []

    def require(self, principal_id, operation, scope_ref):
        self.calls.append((principal_id, operation, scope_ref))
        if (principal_id, operation, scope_ref) in self.denied:
            raise PermissionError("fixture denial")
        return {"principal_id":principal_id, "grant_id":"fixture-only",
            "authority_reference":"fixture-authority-event"}


class MemoryStore:
    """Test-only persistent-shaped fake; each method enforces append-only event history."""
    def __init__(self):
        self.records = {}
        self.keys = {}

    def create_candidate(self, record, *, actor_id, idempotency_key, authorization_reference=""):
        if idempotency_key in self.keys:
            prior = self.records[self.keys[idempotency_key]]
            if prior["content_sha256"] != record["content_sha256"]:
                raise LearningConflict("idempotency key conflict")
            return copy.deepcopy(prior)
        saved = copy.deepcopy(record)
        saved["events"] = [{"event_type":"candidate_created","status_after":"candidate",
            "actor_id":actor_id,"payload":{"authorization_reference":authorization_reference}}]
        self.records[record["record_id"]] = saved
        self.keys[idempotency_key] = record["record_id"]
        return copy.deepcopy(saved)

    def get(self, record_id):
        if record_id not in self.records:
            from riverview_core.resident_execution.resident_learning import LearningNotFound
            raise LearningNotFound("not found")
        return copy.deepcopy(self.records[record_id])

    def transition(self, record_id, revision, expected_status, status_after, *,
                   event_type, actor_id, idempotency_key, payload):
        record = self.records[record_id]
        if record["revision"] != revision or record["status"] != expected_status:
            raise LearningConflict("stale state")
        record["status"] = status_after
        event = {"event_type":event_type,"status_after":status_after,
            "actor_id":actor_id,"idempotency_key":idempotency_key,"payload":copy.deepcopy(payload)}
        record["events"].append(event)
        if "validation" in payload: record["validation"] = copy.deepcopy(payload["validation"])
        if "decision" in payload: record["decision"] = copy.deepcopy(payload["decision"])
        return copy.deepcopy(record)

    def correct(self, old_record_id, revision, record, *, actor_id, idempotency_key, payload):
        old = self.records[old_record_id]
        if old["revision"] != revision or old["status"] != "approved":
            raise LearningConflict("not currently approved")
        old["status"] = "superseded"
        old["events"].append({"event_type":"correction_started","status_after":"superseded",
            "actor_id":actor_id,"idempotency_key":idempotency_key,
            "payload":{"replacement_record_id":record["record_id"],**copy.deepcopy(payload)}})
        return self.create_candidate(record, actor_id=actor_id,
            idempotency_key=idempotency_key+":candidate")

    def rollback(self, record_id, replacement_id, revision, *, actor_id, idempotency_key, payload):
        old, replacement = self.records[record_id], self.records[replacement_id]
        if old["revision"] != revision or old["status"] != "superseded":
            raise LearningConflict("not superseded")
        if replacement.get("supersedes") != record_id:
            raise LearningConflict("wrong replacement")
        if not any(e["status_after"] == "approved" for e in old["events"]):
            raise LearningConflict("not previously approved")
        old["status"] = "approved"
        old["events"].append({"event_type":"rollback_restored","status_after":"approved",
            "actor_id":actor_id,"idempotency_key":idempotency_key+":restore",
            "payload":copy.deepcopy(payload)})
        replacement["status"] = "superseded"
        replacement["events"].append({"event_type":"rollback_superseded","status_after":"superseded",
            "actor_id":actor_id,"idempotency_key":idempotency_key+":replacement","payload":{}})
        return copy.deepcopy(old)

    def list_approved(self, scope_ref, limit):
        rows = [r for r in self.records.values()
            if r["scope_ref"] == scope_ref and r["status"] == "approved"]
        return copy.deepcopy(rows[:limit])


class ResidentLearningTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.auth = FakeAuthorizer()
        self.service = ResidentLearningService(self.store, self.auth)

    def create(self, scope="resident:grace", *, principal="resident:grace", evidence=None):
        return self.service.create_candidate(principal, scope_ref=scope,
            content="Resident learning test fact", evidence=EVIDENCE if evidence is None else evidence,
            provenance={**PROVENANCE,"recorder_id":principal}, classification="confidential",
            retention="bounded_durable", idempotency_key="candidate:"+uuid4().hex)

    def validate(self, record, actor="resident:reviewer"):
        return self.service.validate(actor, record["record_id"], scope_ref=record["scope_ref"],
            expected_revision=record["revision"], result="SUPPORTED",
            evidence_refs=["review://fixture/1"], authority_event_ref="validation-event:test",
            idempotency_key="validate:"+uuid4().hex)

    def approve_shared(self, record):
        return self.service.approve_shared("steward:test", record["record_id"],
            expected_revision=record["revision"], approved_purpose="isolated test",
            authority_event_ref="steward-event:test", idempotency_key="approve:"+uuid4().hex)

    def test_private_candidate_validation_confirmation_and_retrieval(self):
        record = self.create()
        self.assertEqual(record["status"], "candidate")
        self.assertEqual(self.validate(record)["status"], "validated")
        confirmed = self.service.confirm_private("resident:grace", record["record_id"],
            scope_ref="resident:grace", expected_revision=1,
            authority_event_ref="resident-confirm:test",
            idempotency_key="confirm:"+uuid4().hex)
        self.assertEqual(confirmed["status"], "approved")
        self.assertEqual([x["record_id"] for x in self.service.retrieve(
            "resident:grace", scope_ref="resident:grace")], [record["record_id"]])

    def test_private_retention_and_shared_submission_deny_without_authority(self):
        self.auth.denied.add(("resident:grace","candidate_write","resident:grace"))
        with self.assertRaises(AuthorizationDenied): self.create()
        self.auth.denied.add(("resident:grace","candidate_write","institution:riverview"))
        with self.assertRaises(AuthorizationDenied):
            self.create(scope="institution:riverview")
        self.assertEqual(self.store.records, {})

    def test_shared_approval_requires_independent_validation_and_steward(self):
        record = self.create(scope="institution:riverview")
        with self.assertRaises(LearningConflict): self.approve_shared(record)
        validated = self.validate(record)
        approved = self.approve_shared(validated)
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["decision"]["outcome"], "STEWARD_APPROVE")
        self.assertEqual(len(self.service.retrieve("steward:test",
            scope_ref="institution:riverview")), 1)

    def test_rejection_never_enters_retrieval(self):
        record = self.create(scope="institution:riverview")
        rejected = self.service.reject("steward:test", record["record_id"],
            scope_ref="institution:riverview", expected_revision=1,
            reason="insufficient evidence", authority_event_ref="reject-event:test",
            idempotency_key="reject:"+uuid4().hex)
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(self.service.retrieve("steward:test",
            scope_ref="institution:riverview"), [])

    def test_correction_supersedes_old_record_and_rollback_restores_after_revalidation(self):
        record = self.approve_shared(self.validate(self.create(scope="institution:riverview")))
        corrected = self.service.correct("steward:test", record["record_id"],
            scope_ref="institution:riverview", expected_revision=1,
            content="Corrected test fact", evidence=EVIDENCE,
            provenance={**PROVENANCE,"recorder_id":"steward:test"},
            idempotency_key="correct:"+uuid4().hex)
        self.assertEqual(self.store.get(record["record_id"])["status"], "superseded")
        self.validate(corrected)
        restored = self.service.rollback("steward:test", record["record_id"],
            corrected["record_id"], scope_ref="institution:riverview", expected_revision=1,
            revalidation={"result":"SUPPORTED","validator_id":"resident:reviewer",
                "evidence_refs":["source://rechecked"],"authority_event_ref":"recheck:test"},
            idempotency_key="rollback:"+uuid4().hex)
        self.assertEqual(restored["status"], "approved")
        self.assertEqual(self.store.get(corrected["record_id"])["status"], "superseded")
        self.assertEqual(len(self.service.retrieve("steward:test",
            scope_ref="institution:riverview")), 1)
        self.assertIn("rollback_restored", [e["event_type"] for e in restored["events"]])

    def test_missing_identity_or_evidence_fails_before_storage(self):
        with self.assertRaises(LearningValidationError):
            self.create(principal="")
        with self.assertRaises(LearningValidationError):
            self.create(evidence=[])
        self.assertEqual(self.store.records, {})

    def test_cross_resident_private_read_is_denied_before_authorizer(self):
        before = len(self.auth.calls)
        with self.assertRaises(AuthorizationDenied):
            self.service.retrieve("resident:evelyn", scope_ref="resident:grace")
        self.assertEqual(len(self.auth.calls), before)

    def test_service_restart_resumes_durable_store_state(self):
        record = self.approve_shared(self.validate(self.create(scope="institution:riverview")))
        resumed = ResidentLearningService(self.store, self.auth)
        self.assertEqual(resumed.retrieve("steward:test",
            scope_ref="institution:riverview")[0]["record_id"], record["record_id"])


if __name__ == "__main__":
    unittest.main()

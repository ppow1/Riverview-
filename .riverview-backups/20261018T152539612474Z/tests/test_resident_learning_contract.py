# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_learning_contract.py
# Component: RESIDENT-LEARNING-GOVERNANCE
# Revision: 1.0.1
# Purpose: Verify the proposed non-authorizing learning record schema and governance invariants
# Execution Model: Isolated standard-library unittest with jsonschema validation
# Observability: Named schema and scope/approval invariants with deterministic results
# Dependencies: Python 3.10+; jsonschema 4.10.3
# Authority: Uses local fixtures only; never connects to authority or production stores
# Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-GOVERNANCE-001 | Initial contract tests
# Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-GOVERNANCE-001 | Cover classification ceiling for shared scope
# Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md; docs/schemas/resident-learning-record.schema.json
# Tests: This file
# History: Git; new file
# =============================================================================
"""
Tests for the proposed resident learning record envelope.

These checks validate data shape and governance constraints only. They do not
simulate or claim runtime authorization, resident isolation, or approval.
"""

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/schemas/resident-learning-record.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)


def candidate(*, origin="resident:grace", scope=None):
    return {
        "record_id": "learning:123e4567-e89b-12d3-a456-426614174000",
        "revision": 1,
        "originating_resident_id": origin,
        "scope_ref": scope or origin,
        "classification": "confidential",
        "retention": "conversation_policy",
        "status": "candidate",
        "content": "The resident stated a preferred response format.",
        "content_sha256": "a" * 64,
        "evidence": [{
            "source_ref": "conversation://example/sequence/4",
            "source_kind": "resident_statement",
            "captured_at": "2026-10-18T15:00:00Z",
            "source_revision": None,
            "source_sha256": None,
        }],
        "provenance": {
            "recorded_at": "2026-10-18T15:00:01Z",
            "recorder_id": "resident:grace",
            "method": "explicit resident save request",
            "implementation_revision": None,
            "interpretation": "resident_assertion",
        },
        "created_at": "2026-10-18T15:00:01Z",
    }


def approved_private():
    record = candidate()
    record.update({
        "status": "approved",
        "retention": "bounded_durable",
        "validation": {
            "result": "SUPPORTED", "validator_id": "resident:grace",
            "validated_at": "2026-10-18T15:01:00Z", "evidence_refs": ["conversation://example/sequence/4"],
            "authority_event_ref": "event:resident-confirmation:1",
        },
        "decision": {
            "outcome": "RESIDENT_CONFIRM", "actor_id": "resident:grace",
            "decided_at": "2026-10-18T15:01:01Z", "scope_ref": "resident:grace",
            "purpose": "private response preference", "content_sha256": "a" * 64,
            "authority_event_ref": "event:resident-confirmation:1", "reason": "explicit save request",
        },
    })
    return record


class ResidentLearningContractTests(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_evidence_and_provenance_are_required_for_candidate(self):
        record = candidate()
        self.assertEqual(list(VALIDATOR.iter_errors(record)), [])
        del record["evidence"]
        self.assertTrue(list(VALIDATOR.iter_errors(record)))

    def test_candidate_is_not_approved_knowledge(self):
        record = candidate()
        self.assertEqual(record["status"], "candidate")
        self.assertNotIn("decision", record)
        self.assertEqual(list(VALIDATOR.iter_errors(record)), [])

    def test_institutional_scope_requires_approved_steward_decision(self):
        record = candidate(scope="institution:riverview")
        self.assertTrue(list(VALIDATOR.iter_errors(record)))
        record = approved_private()
        record["scope_ref"] = "institution:riverview"
        record["decision"]["scope_ref"] = "institution:riverview"
        record["decision"]["outcome"] = "STEWARD_APPROVE"
        record["decision"]["actor_id"] = "steward:example"
        self.assertEqual(list(VALIDATOR.iter_errors(record)), [])

    def test_institutional_scope_rejects_local_only_classification(self):
        record = approved_private()
        record["scope_ref"] = "institution:riverview"
        record["decision"]["scope_ref"] = "institution:riverview"
        record["decision"]["outcome"] = "STEWARD_APPROVE"
        record["decision"]["actor_id"] = "steward:example"
        record["classification"] = "local_only"
        self.assertTrue(list(VALIDATOR.iter_errors(record)))

    def test_institutional_scope_rejects_resident_confirmation(self):
        record = approved_private()
        record["scope_ref"] = "institution:riverview"
        record["decision"]["scope_ref"] = "institution:riverview"
        self.assertTrue(list(VALIDATOR.iter_errors(record)))

    def test_rejected_proposal_keeps_explicit_rejection_event(self):
        record = candidate()
        record["status"] = "rejected"
        record["decision"] = {
            "outcome": "REJECT", "actor_id": "steward:example",
            "decided_at": "2026-10-18T15:02:00Z", "scope_ref": "resident:grace",
            "purpose": "review", "content_sha256": "a" * 64,
            "authority_event_ref": "event:rejection:1", "reason": "insufficient evidence",
        }
        self.assertEqual(list(VALIDATOR.iter_errors(record)), [])

    def test_supersession_requires_a_new_link_and_audit_event(self):
        record = candidate()
        record["status"] = "superseded"
        record["supersedes"] = "learning:123e4567-e89b-12d3-a456-426614174001"
        record["supersession_event_ref"] = "event:supersession:2"
        self.assertEqual(list(VALIDATOR.iter_errors(record)), [])
        del record["supersession_event_ref"]
        self.assertTrue(list(VALIDATOR.iter_errors(record)))

    def test_unknown_authority_fields_are_rejected(self):
        record = copy.deepcopy(candidate())
        record["grants"] = ["learning.write"]
        self.assertTrue(list(VALIDATOR.iter_errors(record)))

    def test_schema_requires_runtime_resident_identity_check(self):
        record = candidate(origin="resident:evelyn", scope="resident:grace")
        # JSON Schema validates the envelope; identity equality is an authorization
        # invariant the future AuthorityRegistry-backed adapter must enforce.
        self.assertNotEqual(record["scope_ref"], record["originating_resident_id"])
        self.assertEqual(list(VALIDATOR.iter_errors(record)), [])


if __name__ == "__main__":
    unittest.main()
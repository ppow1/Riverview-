# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_institutional_proposals.py
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.1.0
# Purpose: Verify durable proposal records, search, revisions, reviews, and idempotency
# Execution Model: Disposable PostgreSQL schema integration
# Observability: Assertions use synthetic proposal content only
# Dependencies: PostgreSQL 16; Psycopg 3; RIVERVIEW_TEST_PG_DSN
# Authority: Creates and drops only a unique rvtest schema
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Initial proposal registry coverage
# Changed: 2026-10-16 UTC | RV-PROPOSAL-WORK-ORDER-LIFECYCLE-001 | Require dedicated Steward decision API for exact revision approval
# Contracts: docs/components/INSTITUTIONAL_PROPOSALS.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Disposable PostgreSQL contract tests for the institution-wide proposal registry."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import unittest
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class InstitutionalProposalPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.postgres_migrations import apply_migrations
        from riverview_core.resident_execution.proposals import ProposalRegistry

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        apply_migrations(DSN, schema=self.schema,
            migrations_dir=ROOT / "src/riverview_core/migrations")
        apply_migrations(DSN, schema=self.schema,
            migrations_dir=ROOT / "src/riverview_core/institutional_authority/migrations")
        apply_migrations(DSN, schema=self.schema,
            migrations_dir=ROOT / "src/riverview_core/resident_execution/migrations")
        self.registry = ProposalRegistry(DSN, schema=self.schema)
        self.actor = "steward:" + uuid4().hex
        self.source_conversation = str(uuid4())
        self.content = {
            "title": "Solar tracking collection system",
            "summary": "Assess a bounded solar tracking collection prototype.",
            "objective": "Prepare a verified design brief for Steward review.",
            "scope": "Document-only feasibility brief; no procurement or deployment.",
            "proposed_approach": "Retrieve verified records, identify unknowns, and prepare a concise report.",
            "constraints": ["Do not assume equipment is owned."],
            "acceptance_criteria": ["Cite authoritative source records.", "List unknowns explicitly."],
            "tags": ["Solar Energy", "Engineering"],
        }

    def tearDown(self):
        from psycopg import sql
        self.registry.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create(self, *, key="draft:one", content=None):
        return self.registry.create_draft(content or self.content, created_by=self.actor,
            origin_kind="grace_conversation",
            source_references=[{"kind": "resident_conversation", "conversation_id": self.source_conversation,
                                "sequences": [6]}],
            provenance={"provider_id": "local.inference.v1", "served_model": "test-80b",
                        "implementation_id": "implementation:test", "implementation_revision": "a" * 64,
                        "source_conversation_id": self.source_conversation, "source_sequences": [6]},
            idempotency_key=key)

    def test_create_is_draft_searchable_by_title_content_and_casefolded_tag(self):
        saved = self.create()
        self.assertEqual(saved["proposal"]["lifecycle_status"], "DRAFT")
        self.assertEqual(saved["revision"]["tags"], ["solar energy", "engineering"])
        self.assertEqual(len(self.registry.search("solar tracking")["items"]), 1)
        self.assertEqual(len(self.registry.search("authoritative source")["items"]), 1)
        self.assertEqual(len(self.registry.search("engineering")["items"]), 1)
        self.assertEqual(len(self.registry.search(tag="ENGINEERING")["items"]), 1)
        self.assertEqual(self.registry.search("does-not-exist")["items"], [])

    def test_revision_preserves_prior_content_and_requires_compare_and_swap(self):
        saved = self.create()
        proposal_id = saved["proposal"]["proposal_id"]
        revised = dict(self.content, title="Revised solar collection proposal")
        result = self.registry.revise(proposal_id, 1, revised, actor_id=self.actor)
        self.assertEqual(result["proposal"]["current_revision"], 2)
        self.assertEqual(result["revision"]["title"], revised["title"])
        self.assertEqual(self.registry.get(proposal_id, revision=1)["revision"]["title"], self.content["title"])
        from riverview_core.resident_execution.proposals import ProposalConflict
        with self.assertRaises(ProposalConflict):
            self.registry.revise(proposal_id, 1, revised, actor_id=self.actor)

    def test_reviews_are_bound_to_specific_revision_and_keep_findings(self):
        saved = self.create()
        proposal_id = saved["proposal"]["proposal_id"]
        reviewed = self.registry.record_review(proposal_id, 1,
            reviewer_office="office:security", reviewer_principal="resident:ingrid",
            outcome="INSUFFICIENT_EVIDENCE", findings="No active security review was commissioned.",
            conditions=["Do not treat this as an approval."],
            evidence_references=[{"kind": "document", "path": "docs/example.md"}],
            authority_reference="authority:review:test", idempotency_key="review:security:1")
        self.assertEqual(reviewed["reviews"][0]["revision"], 1)
        self.assertEqual(reviewed["reviews"][0]["review_outcome"], "INSUFFICIENT_EVIDENCE")
        self.registry.revise(proposal_id, 1, dict(self.content, title="New revision"), actor_id=self.actor)
        self.assertEqual(self.registry.get(proposal_id, revision=2)["reviews"], [])
        self.assertEqual(len(self.registry.get(proposal_id, revision=1)["reviews"]), 1)

    def test_create_retry_is_idempotent_and_conflicting_content_is_rejected(self):
        first = self.create(key="draft:retry")
        second = self.create(key="draft:retry")
        self.assertEqual(first["proposal"]["proposal_id"], second["proposal"]["proposal_id"])
        from riverview_core.resident_execution.proposals import ProposalConflict
        with self.assertRaises(ProposalConflict):
            self.create(key="draft:retry", content=dict(self.content, title="Different"))
        receipt = self.registry.get_by_idempotency_key("draft:retry", created_by=self.actor)
        self.assertEqual(receipt["proposal"]["proposal_id"], first["proposal"]["proposal_id"])
        self.assertIsNone(self.registry.get_by_idempotency_key("draft:retry", created_by="steward:other"))

    def test_lifecycle_requires_review_state_and_revision_specific_steward_decision(self):
        saved = self.create()
        proposal_id = saved["proposal"]["proposal_id"]
        from riverview_core.resident_execution.proposals import ProposalConflict
        with self.assertRaises(ProposalConflict):
            self.registry.transition(proposal_id, 1, "APPROVED", actor_id=self.actor,
                reason="Skip required review", approved_purpose="prototype", authority_reference="grant:x")
        self.registry.transition(proposal_id, 1, "READY_FOR_REVIEW", actor_id=self.actor,
                                 reason="Draft completed")
        self.registry.transition(proposal_id, 1, "READY_FOR_STEWARD_DECISION", actor_id=self.actor,
                                 reason="Required review disposition recorded")
        with self.assertRaises(ProposalConflict):
            self.registry.transition(proposal_id, 1, "APPROVED", actor_id=self.actor,
                reason="Generic transitions cannot approve work")
        approved = self.registry.steward_decision(proposal_id, 1, decision="APPROVE",
            actor_id=self.actor, reason="Steward approved only the feasibility brief",
            idempotency_key="decision:test:proposal:1",
            expected_content_sha256=self.registry.get(proposal_id, revision=1)["revision"]["content_sha256"],
            approved_purpose="feasibility brief",
            authority_reference="authority:steward-decision:test")
        self.assertEqual(approved["proposal"]["lifecycle_status"], "APPROVED")
        self.assertEqual(approved["events"][-1]["payload"]["approved_purpose"], "feasibility brief")

    def test_bounded_retention_requires_future_expiry_and_is_filtered_after_expiry(self):
        with self.assertRaises(ValueError):
            self.registry.create_draft(self.content, created_by=self.actor,
                origin_kind="authorized_import", source_references=[], provenance={"source": "test"},
                retention_policy="minimum_required")
        # An already-expired row cannot be created through the registry contract.
        expiry = datetime.now(timezone.utc) + timedelta(seconds=1)
        saved = self.registry.create_draft(self.content, created_by=self.actor,
            origin_kind="authorized_import", source_references=[], provenance={"source": "test"},
            privacy_classification="local_only", retention_policy="ephemeral",
            retention_until=expiry, idempotency_key="draft:ephemeral")
        self.assertEqual(saved["proposal"]["privacy_classification"], "local_only")
        import time
        time.sleep(1.1)
        self.assertEqual(self.registry.search("solar tracking")["items"], [])


if __name__ == "__main__":
    unittest.main()

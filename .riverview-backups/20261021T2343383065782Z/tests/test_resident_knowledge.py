# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resident_knowledge.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.2
# Changed: 2026-10-21 UTC | RV-W4-GRACE-GROUNDING-DIAGNOSTICS-20261021 | Verify correlated sanitized selector branch diagnostics
# Purpose: Verify commit-pinned relevant evidence selection and fail-closed bounds
# Execution Model: Temporary committed fixture repository; no live model or database
# Observability: Status, refs, source revision/hash, retrieval completeness, context size
# Dependencies: Python 3.10+; Git
# Authority: Temporary directories only
# Changed: 2026-10-11 UTC | RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE | Initial selector regressions
# Changed: 2026-10-15 UTC | RV-GRACE-GROUNDING-BOUNDED-001 | Cover ranked retrieval when broad objectives match more evidence than the context bound
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Deterministic tests for bounded, commit-pinned resident grounding."""

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
from riverview_core.worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider


RESIDENT_PATHS = (
    "docs/components/RESIDENT_REASONING.md",
    "docs/components/GRACE_OPERATIONAL_INTEGRATION_FLOW.md",
    "docs/components/INSTITUTIONAL_AUTHORITY.md",
    "src/riverview_core/resident_reasoning.py",
    "src/riverview_core/local_reasoning_provider.py",
    "src/riverview_core/worker_adapter/repository_knowledge.py",
    "docs/ROADMAP.md",
)
WORKER_PATHS = (
    "docs/components/WORKER_ADAPTER.md",
    "src/riverview_core/worker_adapter/adapter.py",
    "src/riverview_core/worker_adapter/continuous.py",
    "src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py",
    "src/riverview_core/worker_adapter/repository_knowledge.py",
)


class ResidentKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for path in set(RESIDENT_PATHS + WORKER_PATHS):
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            text = ("# Test fixture\n\n"
                    "The objective work order must preserve repository provenance and "
                    "independent verification.\n\n"
                    "Unrelated context concerns dashboard navigation and browser freshness.\n")
            destination.write_text(text, encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@invalid"],
                       check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Test"],
                       check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "fixture"], check=True)
        self.commit = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True).stdout.strip()

    def tearDown(self):
        self.temp.cleanup()

    def test_selects_relevant_complete_passages_with_commit_and_hash_provenance(self):
        provider = TaskRelevantRepositoryKnowledgeProvider(self.root, self.commit)
        result = provider.ground_assignment({
            "id": "objective:test",
            "contract_ref": provider.CONTRACT_REF,
            "objective": "preserve repository provenance for work order",
            "acceptance_criteria": ["independent verification"],
        })
        self.assertIs(result.status, KnowledgeStatus.VERIFIED)
        self.assertTrue(result.retrieval_complete)
        self.assertEqual(result.source_revision, self.commit)
        self.assertRegex(result.source_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(set(result.source_references),
                         {"repo://" + path for path in RESIDENT_PATHS})
        encoded = str(result.value)
        self.assertIn("independent verification", encoded)
        self.assertNotIn("Unrelated context", encoded)
        self.assertLess(len(__import__("json").dumps(result.value).encode()), 8 * 1024)
        for document in result.value["documents"]:
            self.assertRegex(document["source_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(document["passages"])

    def test_selection_diagnostics_report_contract_branch_without_query_content(self):
        import json

        provider = TaskRelevantRepositoryKnowledgeProvider(self.root, self.commit)
        request_id = "request:grounding-diagnostic"
        assignment_id = "objective:grounding-diagnostic"
        with self.assertLogs(
                "riverview_core.worker_adapter.resident_knowledge", level="INFO") as captured:
            result = provider.ground_assignment({
                "id": assignment_id,
                "contract_ref": "private-contract-sentinel",
                "objective": "private objective content sentinel",
                "acceptance_criteria": ["independent verification"],
            }, diagnostic_context={
                "request_id": request_id,
                "assignment_id": assignment_id,
            })
        diagnostic = json.loads(captured.records[0].getMessage())
        self.assertEqual(result.status, KnowledgeStatus.UNVERIFIED)
        self.assertEqual(diagnostic["request_id"], request_id)
        self.assertEqual(diagnostic["assignment_id"], assignment_id)
        self.assertTrue(diagnostic["contract_ref_present"])
        self.assertFalse(diagnostic["contract_ref_matches"])
        self.assertEqual(diagnostic["selected_branch"], "repository_fallback")
        self.assertGreater(diagnostic["query_term_count"], 0)
        self.assertEqual(diagnostic["rejection_reason"], "BASE_PROVIDER_UNVERIFIED")
        self.assertNotIn("private objective content sentinel", captured.output)
        self.assertNotIn("private-contract-sentinel", captured.output)

    def test_selection_diagnostics_identify_empty_task_query(self):
        import json

        provider = TaskRelevantRepositoryKnowledgeProvider(self.root, self.commit)
        with self.assertLogs(
                "riverview_core.worker_adapter.resident_knowledge", level="INFO") as captured:
            result = provider.ground_assignment({
                "contract_ref": provider.CONTRACT_REF,
                "objective": "objective and the",
                "acceptance_criteria": [],
            })
        diagnostic = json.loads(captured.records[0].getMessage())
        self.assertEqual(result.status, KnowledgeStatus.UNVERIFIED)
        self.assertEqual(diagnostic["selected_branch"], "task_relevant_selection")
        self.assertEqual(diagnostic["query_term_count"], 0)
        self.assertEqual(diagnostic["rejection_reason"], "QUERY_TERMS_EMPTY")

    def test_oversized_evidence_is_incomplete_not_silently_truncated(self):
        provider = TaskRelevantRepositoryKnowledgeProvider(
            self.root, self.commit, max_context_bytes=512)
        result = provider.ground_assignment({
            "id": "objective:test",
            "contract_ref": provider.CONTRACT_REF,
            "objective": "repository provenance independent verification",
        })
        self.assertIs(result.status, KnowledgeStatus.INCOMPLETE)
        self.assertFalse(result.retrieval_complete)
        self.assertEqual(result.source_revision, self.commit)
        self.assertIsNone(result.value)

    def test_broad_query_selects_complete_ranked_passages_under_bound(self):
        provider = TaskRelevantRepositoryKnowledgeProvider(self.root, self.commit)
        documents = []
        references = []
        for path in RESIDENT_PATHS:
            reference = "repo://" + path
            content = "\n\n".join(
                f"Complete paragraph {index}: repository work order independent verification. "
                + ("Context evidence remains source-pinned. " * 7)
                for index in range(30))
            references.append(reference)
            documents.append({"reference": reference, "content": content})
        source_digest = hashlib.sha256("fixture-source-set".encode()).hexdigest()
        verified_source = KnowledgeResult(
            KnowledgeStatus.VERIFIED, value={"documents": documents},
            source_references=tuple(references), source_revision=self.commit,
            source_sha256=source_digest, retrieval_complete=True)
        provider.repository.ground_assignment = lambda _assignment: verified_source

        result = provider.ground_assignment({
            "id": "objective:broad",
            "contract_ref": provider.CONTRACT_REF,
            "objective": "repository work order independent verification",
        })

        self.assertIs(result.status, KnowledgeStatus.VERIFIED)
        self.assertTrue(result.retrieval_complete)
        self.assertEqual(result.source_references, tuple(references))
        encoded = __import__("json").dumps(
            result.value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(encoded), provider.MAX_SELECTION_BYTES)
        self.assertEqual(result.value["selection_policy"],
                         "ranked-complete-paragraphs-v1")
        self.assertEqual(result.value["query_term_coverage"],
                         {"matched": 3, "selected": 3})
        self.assertLess(sum(len(document["passages"])
                            for document in result.value["documents"]), 30 * len(RESIDENT_PATHS))
        for document in result.value["documents"]:
            original = next(item["content"] for item in documents
                            if item["reference"] == document["reference"])
            whole_paragraphs = set(provider._paragraphs(original))
            for passage in document["passages"]:
                self.assertIn((passage["line_start"], passage["line_end"],
                               passage["text"]), whole_paragraphs)

    def test_unknown_or_unmatched_objective_does_not_claim_verification(self):
        provider = TaskRelevantRepositoryKnowledgeProvider(self.root, self.commit)
        unknown = provider.ground_assignment({"contract_ref": "repo://unknown"})
        no_query = provider.ground_assignment({
            "contract_ref": provider.CONTRACT_REF, "objective": "and or the"
        })
        self.assertIs(unknown.status, KnowledgeStatus.NO_MATCH)
        self.assertIs(no_query.status, KnowledgeStatus.UNVERIFIED)


if __name__ == "__main__":
    unittest.main()

# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: src/riverview_core/worker_adapter/knowledge_provider_v1/test_contract.py
# Component: KNOWLEDGE-PROVIDER-CONTRACT
# Revision: 1.0.3
# Purpose: Verify stable v1 signatures, statuses, provenance validation, and fallback
# Execution Model: Standalone standard-library unittest contract suite
# Observability: unittest assertions and exit status
# Dependencies: Python 3.10+; package-local files only
# Authority: No database, secret, network, or Camrui runtime dependency
# Changed: 2026-10-10 UTC | RV-KNOWLEDGE-IFACE-001 | Check completeness and independent execution
# Contracts: README.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
import unittest

try:
    from .contract import KnowledgeResult, KnowledgeStatus, UnavailableKnowledgeProvider
    from .mock_provider import MockKnowledgeProvider
except ImportError:
    from contract import KnowledgeResult, KnowledgeStatus, UnavailableKnowledgeProvider
    from mock_provider import MockKnowledgeProvider


class KnowledgeProviderContractTests(unittest.TestCase):
    def test_mock_implements_all_four_operations_with_verified_provenance(self):
        provider = MockKnowledgeProvider("known contract")
        assignment = {"id": "assignment-1", "objective_ref": "objective:1"}
        self.assertEqual(provider.ground_assignment(assignment).status,
                         KnowledgeStatus.VERIFIED)
        self.assertEqual(provider.preflight_action(assignment, "command.v1").value,
                         "known contract")
        self.assertEqual(provider.reground_assignment(assignment, "handoff").source_revision,
                         "1.0.0")
        self.assertEqual(provider.record_learning(assignment, {"result": "ok"}).status,
                         KnowledgeStatus.UNVERIFIED)

    def test_default_provider_never_claims_verification(self):
        provider = UnavailableKnowledgeProvider()
        assignment = {"id": "assignment-1"}
        for result in (provider.ground_assignment(assignment),
                       provider.preflight_action(assignment, "action"),
                       provider.reground_assignment(assignment, "restart"),
                       provider.record_learning(assignment, {})):
            self.assertEqual(result.status, KnowledgeStatus.UNAVAILABLE)

    def test_verified_requires_source_and_hash_is_well_formed(self):
        with self.assertRaises(ValueError):
            KnowledgeResult(KnowledgeStatus.VERIFIED)
        with self.assertRaises(ValueError):
            KnowledgeResult(KnowledgeStatus.VERIFIED, source_references=("urn:x",),
                            retrieval_complete=True, source_sha256="not-a-hash")
        with self.assertRaises(ValueError):
            KnowledgeResult(KnowledgeStatus.VERIFIED, source_references=("../escape",),
                            retrieval_complete=True)

    def test_incomplete_retrieval_cannot_claim_completeness(self):
        with self.assertRaises(ValueError):
            KnowledgeResult(KnowledgeStatus.INCOMPLETE, retrieval_complete=True)

    def test_all_machine_statuses_are_stable(self):
        self.assertEqual({status.value for status in KnowledgeStatus},
                         {"VERIFIED", "NO_MATCH", "UNAVAILABLE", "INCOMPLETE",
                          "CONTRADICTORY", "UNVERIFIED"})


if __name__ == "__main__":
    unittest.main()

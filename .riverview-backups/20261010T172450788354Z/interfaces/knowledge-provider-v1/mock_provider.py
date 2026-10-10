# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: interfaces/knowledge-provider-v1/mock_provider.py
# Component: KNOWLEDGE-PROVIDER-CONTRACT
# Revision: 1.0.0
# Purpose: Demonstrate a conforming fake provider for independent contract testing
# Execution Model: In-process deterministic mock
# Observability: Fixed VERIFIED responses with explicit provenance
# Dependencies: Python 3.10+; contract.py
# Authority: Test/example only; not institutional retrieval or verification
# Changed: 2026-10-10 UTC | RV-KNOWLEDGE-IFACE-001 | Initial mock provider
# Contracts: interfaces/knowledge-provider-v1/README.md
# Tests: interfaces/knowledge-provider-v1/test_contract.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
from .contract import KnowledgeResult, KnowledgeStatus


class MockKnowledgeProvider:
    """Test fixture only; its configured facts are not real retrieved knowledge."""

    def __init__(self, value="mock fact"):
        self.value = value

    def _result(self):
        return KnowledgeResult(KnowledgeStatus.VERIFIED, self.value,
                               ("urn:example:mock-source:1",), "1.0.0", "0" * 64)

    def ground_assignment(self, assignment):
        return self._result()

    def preflight_action(self, assignment, action):
        return self._result()

    def reground_assignment(self, assignment, trigger):
        return self._result()

    def record_learning(self, assignment, outcome):
        return KnowledgeResult(KnowledgeStatus.UNVERIFIED)

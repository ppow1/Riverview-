<!--
Riverview~ Controlled Document
File: docs/components/REPOSITORY_KNOWLEDGE_FLOW.md
Component: REPOSITORY-KNOWLEDGE-PROVIDER
Document Revision: 1.0.3
Purpose: Display pinned contract retrieval, failure and worker handoff
Authority: A source lookup cannot grant work authority
Changed: 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE-MD-LINT | Remove trailing whitespace
Generated from: process_graphs/knowledge-provider/repository-contracts.json
History: Git and .riverview-backups/manifest.jsonl
-->
# Repository knowledge retrieval and handoff

**Canonical workflow:** `rv:repository-knowledge-provider:pinned-worker-contracts`
**Generated from:** canonical JSON graph; do not hand-edit the Mermaid block.
**Cookbook:** [diagnosis and recovery](REPOSITORY_KNOWLEDGE_COOKBOOK.md)

```mermaid
flowchart LR
  subgraph g_rv_repository_knowledge_provider_pinned_worker_contracts["REPOSITORY-KNOWLEDGE-PROVIDER / pinned-worker-contracts.v1"]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_intake_ffe645c5(["Worker requests one registered contract reference"])
    g_rv_repository_knowledge_provider_pinned_worker_contracts_resolve_a1d9ecb0["Resolve exact allowlisted contract or action mapping"]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_pin_8bbe1dd5["Require full source commit to match the approved pin"]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_integrity_e62aa934{"Are all configured source bytes clean and checksum-valid?"}
    g_rv_repository_knowledge_provider_pinned_worker_contracts_read_9b3ffad0["Read only the bounded fixed source set"]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_verified_a6649bc2["Return complete source refs, revision and aggregate hash"]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_no_match_bbb3531d[["Unknown contract or action returns NO_MATCH"]]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_unverified_f386eeaa[["Pin or source integrity failure returns UNVERIFIED"]]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_incomplete_62739468[["Source exceeds a fixed retrieval bound"]]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_unavailable_331b6143[["Git, package metadata or source read unavailable"]]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_wait_11903ed7[["Non-VERIFIED lookups keep only this assignment waiting"]]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_worker_ground_889c660c["Return source evidence to the existing worker grounding gate"]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_worker_wait_ef15ef99["Route non-verified outcomes to the existing assignment-local wait"]
    g_rv_repository_knowledge_provider_pinned_worker_contracts_learning_unavailable_384ee769[["Learning write is explicitly unavailable in this read-only provider"]]
  end
  g_rv_worker_adapter_deterministic_attempt_ground_c2193741["Registered target<br/>rv:worker-adapter:deterministic-attempt"]
  g_rv_worker_adapter_deterministic_attempt_evidence_wait_e57f58d4["Registered target<br/>rv:worker-adapter:deterministic-attempt"]
  g_rv_worker_adapter_deterministic_attempt_learning_83260d87["Registered target<br/>rv:worker-adapter:deterministic-attempt"]
  g_rv_repository_knowledge_provider_pinned_worker_contracts_intake_ffe645c5 --> g_rv_repository_knowledge_provider_pinned_worker_contracts_resolve_a1d9ecb0
  g_rv_repository_knowledge_provider_pinned_worker_contracts_resolve_a1d9ecb0 -->|diagnostic_branch: No registered contract/action| g_rv_repository_knowledge_provider_pinned_worker_contracts_no_match_bbb3531d
  g_rv_repository_knowledge_provider_pinned_worker_contracts_resolve_a1d9ecb0 -->|Known mapping| g_rv_repository_knowledge_provider_pinned_worker_contracts_pin_8bbe1dd5
  g_rv_repository_knowledge_provider_pinned_worker_contracts_pin_8bbe1dd5 -->|Exact commit| g_rv_repository_knowledge_provider_pinned_worker_contracts_integrity_e62aa934
  g_rv_repository_knowledge_provider_pinned_worker_contracts_pin_8bbe1dd5 -->|diagnostic_branch: Commit mismatch| g_rv_repository_knowledge_provider_pinned_worker_contracts_unverified_f386eeaa
  g_rv_repository_knowledge_provider_pinned_worker_contracts_integrity_e62aa934 -->|Sources clean and checksummed| g_rv_repository_knowledge_provider_pinned_worker_contracts_read_9b3ffad0
  g_rv_repository_knowledge_provider_pinned_worker_contracts_integrity_e62aa934 -->|diagnostic_branch: Dirty/tampered bytes| g_rv_repository_knowledge_provider_pinned_worker_contracts_unverified_f386eeaa
  g_rv_repository_knowledge_provider_pinned_worker_contracts_read_9b3ffad0 -->|verification| g_rv_repository_knowledge_provider_pinned_worker_contracts_verified_a6649bc2
  g_rv_repository_knowledge_provider_pinned_worker_contracts_read_9b3ffad0 -->|diagnostic_branch: Size limit| g_rv_repository_knowledge_provider_pinned_worker_contracts_incomplete_62739468
  g_rv_repository_knowledge_provider_pinned_worker_contracts_read_9b3ffad0 -->|diagnostic_branch: Read/metadata failure| g_rv_repository_knowledge_provider_pinned_worker_contracts_unavailable_331b6143
  g_rv_repository_knowledge_provider_pinned_worker_contracts_verified_a6649bc2 --> g_rv_repository_knowledge_provider_pinned_worker_contracts_worker_ground_889c660c
  g_rv_repository_knowledge_provider_pinned_worker_contracts_worker_ground_889c660c -->|jump| g_rv_worker_adapter_deterministic_attempt_ground_c2193741
  g_rv_repository_knowledge_provider_pinned_worker_contracts_no_match_bbb3531d --> g_rv_repository_knowledge_provider_pinned_worker_contracts_wait_11903ed7
  g_rv_repository_knowledge_provider_pinned_worker_contracts_unverified_f386eeaa --> g_rv_repository_knowledge_provider_pinned_worker_contracts_wait_11903ed7
  g_rv_repository_knowledge_provider_pinned_worker_contracts_incomplete_62739468 --> g_rv_repository_knowledge_provider_pinned_worker_contracts_wait_11903ed7
  g_rv_repository_knowledge_provider_pinned_worker_contracts_unavailable_331b6143 --> g_rv_repository_knowledge_provider_pinned_worker_contracts_wait_11903ed7
  g_rv_repository_knowledge_provider_pinned_worker_contracts_wait_11903ed7 --> g_rv_repository_knowledge_provider_pinned_worker_contracts_worker_wait_ef15ef99
  g_rv_repository_knowledge_provider_pinned_worker_contracts_worker_wait_ef15ef99 -->|jump| g_rv_worker_adapter_deterministic_attempt_evidence_wait_e57f58d4
  g_rv_repository_knowledge_provider_pinned_worker_contracts_learning_unavailable_384ee769 -->|documentation| g_rv_worker_adapter_deterministic_attempt_learning_83260d87
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

## Diagnostic mapping

| Stable node | Expected evidence | Failure meaning | Safe resume |
|---|---|---|---|
| `rv:repository-knowledge-provider:pinned-worker-contracts:pin` | Runtime/package commit equals approved full commit | Source identity is stale or unapproved | Rebuild/publish exact pinned package; lookup again |
| `rv:repository-knowledge-provider:pinned-worker-contracts:integrity` | Clean tracked sources or matching package digests | Source bytes may differ from verified commit | Preserve current evidence and install an exact package |
| `rv:repository-knowledge-provider:pinned-worker-contracts:read` | All bounded source files decode | Missing, oversized or invalid source | Keep work waiting; repair the package/contract revision |
| `rv:repository-knowledge-provider:pinned-worker-contracts:verified` | Complete result with refs/revision/hash | Source retrieval verified; not action authorization | Worker continues to its independent authority and verification gates |

## Revision history

- **1.0.3 — 2026-10-11:** Remove trailing whitespace from generated-view metadata.
- **1.0.2 — 2026-10-11:** Add the flow document's revision history.
- **1.0.1 — 2026-10-11:** Generate synchronized flow from the registered canonical graph.
- **1.0.0 — 2026-10-11:** Establish the workflow view contract.

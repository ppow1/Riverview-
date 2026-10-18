<!-- Riverview~ Controlled Document
File: docs/components/RESIDENT_LEARNING_FLOW.md
Component: RESIDENT-LEARNING-GOVERNANCE
File Revision: 1.0.1
Purpose: Focused generated lifecycle, denial, diagnostics, and recovery graph
Execution Model: Static generated projection; no runtime execution
Observability: Every branch terminates in a typed denial, pending state, or authorized recovery
Dependencies: process_graphs/resident-learning/lifecycle.json; scripts/process_graph.py
Authority: Describes existing contract and grants no permission
Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Add focused resident-learning lifecycle graph projection
Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md
Tests: python scripts/process_graph.py check; tests/test_process_graph.py
History: Git and .riverview-backups/manifest.jsonl
-->

# Resident learning lifecycle

This view is generated from `process_graphs/resident-learning/lifecycle.json`.

```mermaid
flowchart LR
  subgraph g_rv_resident_learning_lifecycle["RESIDENT-LEARNING-GOVERNANCE / resident.learning.lifecycle.v1"]
    g_rv_resident_learning_lifecycle_binding_45206f14["Refresh authenticated office binding and require a current resident principal"]
    g_rv_resident_learning_lifecycle_candidate_767365d6(["Accept evidence-bearing candidate only after exact authorization"])
    g_rv_resident_learning_lifecycle_validate_0125bbd9["Independent reviewer records supported, contradicted, or insufficient result"]
    g_rv_resident_learning_lifecycle_approve_8bfa62dd{"Require resident confirmation for private retention or Steward approval for institutional sharing"}
    g_rv_resident_learning_lifecycle_retrieve_962581da["Return only approved knowledge in the exact authorized scope"]
    g_rv_resident_learning_lifecycle_correct_a542a5b8["Append correction, supersession, or fresh-evidence rollback events"]
    g_rv_resident_learning_lifecycle_denied_23755e6a[["Deny when identity, exact scope authority, or evidence is absent or stale"]]
    g_rv_resident_learning_lifecycle_reject_df2e0331{"Reject or defer unsupported candidates; keep them out of retrieval"}
    g_rv_resident_learning_lifecycle_unavailable_a606e812[["Authority or store unavailable; preserve pending state and fail closed"]]
    g_rv_resident_learning_lifecycle_diagnose_622d91ac["Read-only diagnosis checks event history, scope, evidence, and store health"]
    g_rv_resident_learning_lifecycle_recover_a65add3d["Resume only after dependency recovery and recheck current authority and idempotency"]
    g_rv_resident_learning_lifecycle_rollback_check_d7810158{"Require fresh evidence and current approval before restoring a prior revision"}
  end
  g_rv_resident_learning_lifecycle_binding_45206f14 --> g_rv_resident_learning_lifecycle_candidate_767365d6
  g_rv_resident_learning_lifecycle_candidate_767365d6 --> g_rv_resident_learning_lifecycle_validate_0125bbd9
  g_rv_resident_learning_lifecycle_validate_0125bbd9 --> g_rv_resident_learning_lifecycle_approve_8bfa62dd
  g_rv_resident_learning_lifecycle_approve_8bfa62dd --> g_rv_resident_learning_lifecycle_retrieve_962581da
  g_rv_resident_learning_lifecycle_retrieve_962581da --> g_rv_resident_learning_lifecycle_correct_a542a5b8
  g_rv_resident_learning_lifecycle_correct_a542a5b8 --> g_rv_resident_learning_lifecycle_validate_0125bbd9
  g_rv_resident_learning_lifecycle_binding_45206f14 -->|diagnostic_branch: unknown or stale identity| g_rv_resident_learning_lifecycle_denied_23755e6a
  g_rv_resident_learning_lifecycle_candidate_767365d6 -->|diagnostic_branch: exact write grant or evidence missing| g_rv_resident_learning_lifecycle_denied_23755e6a
  g_rv_resident_learning_lifecycle_validate_0125bbd9 -->|diagnostic_branch: contradicted or insufficient evidence| g_rv_resident_learning_lifecycle_reject_df2e0331
  g_rv_resident_learning_lifecycle_reject_df2e0331 -->|verification: candidate remains excluded| g_rv_resident_learning_lifecycle_retrieve_962581da
  g_rv_resident_learning_lifecycle_approve_8bfa62dd -->|diagnostic_branch: authority/store unavailable| g_rv_resident_learning_lifecycle_unavailable_a606e812
  g_rv_resident_learning_lifecycle_unavailable_a606e812 -->|recovery_route: read-only checks only| g_rv_resident_learning_lifecycle_diagnose_622d91ac
  g_rv_resident_learning_lifecycle_diagnose_622d91ac -->|recovery_route: dependency restored| g_rv_resident_learning_lifecycle_recover_a65add3d
  g_rv_resident_learning_lifecycle_recover_a65add3d -->|verification: refresh identity and exact authorization| g_rv_resident_learning_lifecycle_binding_45206f14
  g_rv_resident_learning_lifecycle_correct_a542a5b8 -->|diagnostic_branch: proposed rollback| g_rv_resident_learning_lifecycle_rollback_check_d7810158
  g_rv_resident_learning_lifecycle_rollback_check_d7810158 -->|recovery_route: prior revision re-enters current validation| g_rv_resident_learning_lifecycle_validate_0125bbd9
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

See the [implementation cookbook](RESIDENT_LEARNING_COOKBOOK.md) for safe local checks, diagnosis, and restoration steps. This graph is descriptive; it does not turn on a caller or create any authority.

# Independent outcome verification

**Document Revision:** 1.0.1  
**Component:** OUTCOME-VERIFIER  
**Milestone:** M2.2  
**Status:** IN PROGRESS — isolated PostgreSQL engineering; not deployed  
**Canonical source:** `process_graphs/outcome-verifier/independent-result.json`

The canonical graph distinguishes persisted worker output from verification,
records verifier identity and criteria, and routes accepted, rejected, and
inconclusive decisions to separate state outcomes. Mermaid is generated with
`python3 scripts/process_graph.py generate`.

```mermaid
flowchart LR
  subgraph g_rv_outcome_verifier_independent_result["OUTCOME-VERIFIER / deterministic-result-verification.v1"]
    g_rv_outcome_verifier_independent_result_verification_intake_faa4dd99(["Receive a persisted worker attempt awaiting verification"])
    g_rv_outcome_verifier_independent_result_result_jump_698bbb3f["Load persisted attempt and result from M2.1 worker ledger"]
    g_rv_outcome_verifier_independent_result_identity_check_6a2169fa["Authenticate separate verifier capability and enforce authority scope"]
    g_rv_outcome_verifier_independent_result_evaluate_1f05e061["Recompute result checks independently from executor claim"]
    g_rv_outcome_verifier_independent_result_decision_5500806a{"Classify acceptance against explicit criteria and evidence"}
    g_rv_outcome_verifier_independent_result_accepted_record_20153938["Persist ACCEPTED criteria, verifier provenance, and evidence"]
    g_rv_outcome_verifier_independent_result_complete_88d049f1(["Complete only after independent ACCEPTED record exists"])
    g_rv_outcome_verifier_independent_result_reject_7fa28bea[["Reject invalid artifact and preserve failed criteria"]]
    g_rv_outcome_verifier_independent_result_rework_1f65b6f0["Route rejected result to durable rework_required assignment state"]
    g_rv_outcome_verifier_independent_result_inconclusive_66937493[["Keep inconclusive result blocked for reassessment"]]
  end
  g_rv_worker_adapter_deterministic_attempt_result_12aa9ef4["Registered target<br/>rv:worker-adapter:deterministic-attempt"]
  g_rv_outcome_verifier_independent_result_verification_intake_faa4dd99 --> g_rv_outcome_verifier_independent_result_result_jump_698bbb3f
  g_rv_outcome_verifier_independent_result_result_jump_698bbb3f -->|jump| g_rv_worker_adapter_deterministic_attempt_result_12aa9ef4
  g_rv_outcome_verifier_independent_result_verification_intake_faa4dd99 --> g_rv_outcome_verifier_independent_result_identity_check_6a2169fa
  g_rv_outcome_verifier_independent_result_identity_check_6a2169fa --> g_rv_outcome_verifier_independent_result_evaluate_1f05e061
  g_rv_outcome_verifier_independent_result_evaluate_1f05e061 --> g_rv_outcome_verifier_independent_result_decision_5500806a
  g_rv_outcome_verifier_independent_result_decision_5500806a -->|verification: all required criteria pass| g_rv_outcome_verifier_independent_result_accepted_record_20153938
  g_rv_outcome_verifier_independent_result_accepted_record_20153938 -->|verification| g_rv_outcome_verifier_independent_result_complete_88d049f1
  g_rv_outcome_verifier_independent_result_decision_5500806a -->|diagnostic_branch: invalid result| g_rv_outcome_verifier_independent_result_reject_7fa28bea
  g_rv_outcome_verifier_independent_result_reject_7fa28bea -->|recovery_route| g_rv_outcome_verifier_independent_result_rework_1f65b6f0
  g_rv_outcome_verifier_independent_result_decision_5500806a -->|escalation: evidence does not support acceptance| g_rv_outcome_verifier_independent_result_inconclusive_66937493
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

Revision history: 1.0.0 — initial M2.2 independent result verification view.

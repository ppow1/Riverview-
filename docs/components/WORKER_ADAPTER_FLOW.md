# Riverview~ worker adapter flow

**Document Revision:** 1.0.5
**Component:** WORKER-ADAPTER
**Canonical workflow:** `process_graphs/worker-adapter/deterministic-attempt.json`
**Generated from:** canonical workflow JSON; do not edit the Mermaid projection by hand.

```mermaid
flowchart LR
  subgraph g_rv_worker_adapter_deterministic_attempt["WORKER-ADAPTER / deterministic-attempt.v1"]
    g_rv_worker_adapter_deterministic_attempt_request_7dff0e33(["Deterministic worker request"])
    g_rv_worker_adapter_deterministic_attempt_authenticate_1608feb4["Verify random credential digest, active registration, and scope"]
    g_rv_worker_adapter_deterministic_attempt_auth_fail_78cfc724[["Reject invalid token, capability, or assignment authority scope"]]
    g_rv_worker_adapter_deterministic_attempt_claim_ad2357b6["Claim oldest ready assignment inside authenticated scope"]
    g_rv_worker_adapter_deterministic_attempt_lease_582df0fd["Require current M1.4 assignment fencing generation"]
    g_rv_worker_adapter_deterministic_attempt_lease_jump_5863cf02["Resolve lease and fencing contract in M1.4 scheduler"]
    g_rv_worker_adapter_deterministic_attempt_begin_9ea07cfe["Persist attributable attempt before deterministic result computation"]
    g_rv_worker_adapter_deterministic_attempt_compute_6725940c["Run deterministic local SHA-256 capability"]
    g_rv_worker_adapter_deterministic_attempt_complete_check_6605f820["Recheck current lease before durable result commit"]
    g_rv_worker_adapter_deterministic_attempt_lost_17b81010[["Persist lease_lost attempt and reject stale result"]]
    g_rv_worker_adapter_deterministic_attempt_result_12aa9ef4["Persist result, digest, and successful attempt status"]
    g_rv_worker_adapter_deterministic_attempt_loss_query_cbfb3695["Expose unfinished attempts for worker-loss detection"]
    g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4(["Continuously poll for one independently claimable assignment"])
    g_rv_worker_adapter_deterministic_attempt_ground_c2193741["Ground assignment against the replaceable knowledge provider"]
    g_rv_worker_adapter_deterministic_attempt_ground_gate_bfc2d024{"Is assignment grounding VERIFIED and retrieval complete?"}
    g_rv_worker_adapter_deterministic_attempt_preflight_70fdc212["Preflight the action contract before execution"]
    g_rv_worker_adapter_deterministic_attempt_preflight_gate_ce23b57c{"Is the requested action preflight VERIFIED?"}
    g_rv_worker_adapter_deterministic_attempt_reground_5d56433b["Refresh assignment context before action or on a recovery trigger"]
    g_rv_worker_adapter_deterministic_attempt_reground_gate_f5063204{"Is the current assignment context VERIFIED?"}
    g_rv_worker_adapter_deterministic_attempt_evidence_wait_e57f58d4[["Persist non-verified status and wait for evidence for this assignment only"]]
    g_rv_worker_adapter_deterministic_attempt_action_cef7346f["Invoke action only after durable effect-classified intent"]
    g_rv_worker_adapter_deterministic_attempt_action_failure_d12eae6a[["Record assignment-local failure and reground without stopping other polls"]]
    g_rv_worker_adapter_deterministic_attempt_learning_83260d87["Persist learning outcome and provenance without automatic promotion"]
    g_rv_worker_adapter_deterministic_attempt_cycle_recovery_addf7cd2["Reconcile expired leases after interruption with effect-aware durable recovery"]
    g_rv_worker_adapter_deterministic_attempt_steward_shutdown_974b0b16(["Stop polling only when explicit Steward shutdown control is asserted"])
    g_rv_worker_adapter_deterministic_attempt_recovery_intent_d549a47e["Persist effect class before invoking the worker action"]
    g_rv_worker_adapter_deterministic_attempt_recovery_scan_12e05359["Select expired running leases at startup or recovery poll"]
    g_rv_worker_adapter_deterministic_attempt_recovery_policy_13bb5685{"Can this incomplete effect be safely repeated?"}
    g_rv_worker_adapter_deterministic_attempt_recovery_retry_cd947e91["Fence prior generation and requeue only retry-safe work"]
    g_rv_worker_adapter_deterministic_attempt_recovery_unknown_673fc7f3[["Hold unknown external outcome in awaiting_steward"]]
    g_rv_worker_adapter_deterministic_attempt_recovery_preserve_f9e86f59["Preserve durable result and continue to independent verification"]
    g_rv_worker_adapter_deterministic_attempt_recovery_audit_fb03175c["Persist one decision per assignment and lease generation"]
    g_rv_worker_adapter_deterministic_attempt_verification_jump_0fedcb93["Continue preserved results at independent verifier"]
  end
  g_rv_assignment_scheduler_independent_claims_start_check_f588e935["Registered target<br/>rv:assignment-scheduler:independent-claims"]
  g_rv_outcome_verifier_independent_result_verification_intake_faa4dd99["Registered target<br/>rv:outcome-verifier:independent-result"]
  g_rv_worker_adapter_deterministic_attempt_request_7dff0e33 --> g_rv_worker_adapter_deterministic_attempt_authenticate_1608feb4
  g_rv_worker_adapter_deterministic_attempt_authenticate_1608feb4 -->|diagnostic_branch: Credential, capability, or scope rejected| g_rv_worker_adapter_deterministic_attempt_auth_fail_78cfc724
  g_rv_worker_adapter_deterministic_attempt_lease_582df0fd -->|Current lease| g_rv_worker_adapter_deterministic_attempt_begin_9ea07cfe
  g_rv_worker_adapter_deterministic_attempt_lease_jump_5863cf02 -->|jump: Follow current M1.4 lease validation| g_rv_assignment_scheduler_independent_claims_start_check_f588e935
  g_rv_worker_adapter_deterministic_attempt_begin_9ea07cfe --> g_rv_worker_adapter_deterministic_attempt_compute_6725940c
  g_rv_worker_adapter_deterministic_attempt_compute_6725940c --> g_rv_worker_adapter_deterministic_attempt_complete_check_6605f820
  g_rv_worker_adapter_deterministic_attempt_complete_check_6605f820 -->|diagnostic_branch: Lease expired or fenced| g_rv_worker_adapter_deterministic_attempt_lost_17b81010
  g_rv_worker_adapter_deterministic_attempt_complete_check_6605f820 -->|Current lease| g_rv_worker_adapter_deterministic_attempt_result_12aa9ef4
  g_rv_worker_adapter_deterministic_attempt_begin_9ea07cfe -->|diagnostic_branch: Process stops before result commit| g_rv_worker_adapter_deterministic_attempt_loss_query_cbfb3695
  g_rv_worker_adapter_deterministic_attempt_lease_582df0fd -->|prerequisite: M1.4 lease table/token contract; not a runtime call| g_rv_assignment_scheduler_independent_claims_start_check_f588e935
  g_rv_worker_adapter_deterministic_attempt_authenticate_1608feb4 -->|Credential and capability valid| g_rv_worker_adapter_deterministic_attempt_claim_ad2357b6
  g_rv_worker_adapter_deterministic_attempt_claim_ad2357b6 -->|Exact scope match| g_rv_worker_adapter_deterministic_attempt_lease_582df0fd
  g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4 -->|poll| g_rv_worker_adapter_deterministic_attempt_claim_ad2357b6
  g_rv_worker_adapter_deterministic_attempt_claim_ad2357b6 -->|claimed task| g_rv_worker_adapter_deterministic_attempt_ground_c2193741
  g_rv_worker_adapter_deterministic_attempt_ground_c2193741 --> g_rv_worker_adapter_deterministic_attempt_ground_gate_bfc2d024
  g_rv_worker_adapter_deterministic_attempt_ground_gate_bfc2d024 -->|diagnostic_branch: not VERIFIED| g_rv_worker_adapter_deterministic_attempt_evidence_wait_e57f58d4
  g_rv_worker_adapter_deterministic_attempt_ground_gate_bfc2d024 -->|VERIFIED| g_rv_worker_adapter_deterministic_attempt_preflight_70fdc212
  g_rv_worker_adapter_deterministic_attempt_preflight_70fdc212 --> g_rv_worker_adapter_deterministic_attempt_preflight_gate_ce23b57c
  g_rv_worker_adapter_deterministic_attempt_preflight_gate_ce23b57c -->|diagnostic_branch: not VERIFIED| g_rv_worker_adapter_deterministic_attempt_evidence_wait_e57f58d4
  g_rv_worker_adapter_deterministic_attempt_preflight_gate_ce23b57c -->|VERIFIED| g_rv_worker_adapter_deterministic_attempt_reground_5d56433b
  g_rv_worker_adapter_deterministic_attempt_reground_5d56433b --> g_rv_worker_adapter_deterministic_attempt_reground_gate_f5063204
  g_rv_worker_adapter_deterministic_attempt_reground_gate_f5063204 -->|diagnostic_branch: not VERIFIED| g_rv_worker_adapter_deterministic_attempt_evidence_wait_e57f58d4
  g_rv_worker_adapter_deterministic_attempt_reground_gate_f5063204 -->|VERIFIED| g_rv_worker_adapter_deterministic_attempt_action_cef7346f
  g_rv_worker_adapter_deterministic_attempt_action_cef7346f -->|diagnostic_branch: assignment-local failure| g_rv_worker_adapter_deterministic_attempt_action_failure_d12eae6a
  g_rv_worker_adapter_deterministic_attempt_action_failure_d12eae6a -->|recovery_route: failure context| g_rv_worker_adapter_deterministic_attempt_reground_5d56433b
  g_rv_worker_adapter_deterministic_attempt_evidence_wait_e57f58d4 -->|continue unrelated work| g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4
  g_rv_worker_adapter_deterministic_attempt_learning_83260d87 -->|next poll| g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4
  g_rv_worker_adapter_deterministic_attempt_cycle_recovery_addf7cd2 -->|recovery_route: resume polling| g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4
  g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4 -->|escalation: explicit Steward stop| g_rv_worker_adapter_deterministic_attempt_steward_shutdown_974b0b16
  g_rv_worker_adapter_deterministic_attempt_reground_gate_f5063204 -->|VERIFIED before action| g_rv_worker_adapter_deterministic_attempt_recovery_intent_d549a47e
  g_rv_worker_adapter_deterministic_attempt_recovery_intent_d549a47e -->|durable intent exists| g_rv_worker_adapter_deterministic_attempt_action_cef7346f
  g_rv_worker_adapter_deterministic_attempt_cycle_recovery_addf7cd2 -->|recovery_route: startup or recovery polling boundary| g_rv_worker_adapter_deterministic_attempt_recovery_scan_12e05359
  g_rv_worker_adapter_deterministic_attempt_recovery_scan_12e05359 -->|expired lease locked| g_rv_worker_adapter_deterministic_attempt_recovery_policy_13bb5685
  g_rv_worker_adapter_deterministic_attempt_recovery_scan_12e05359 -->|diagnostic_branch: result already committed| g_rv_worker_adapter_deterministic_attempt_recovery_preserve_f9e86f59
  g_rv_worker_adapter_deterministic_attempt_recovery_preserve_f9e86f59 --> g_rv_worker_adapter_deterministic_attempt_recovery_audit_fb03175c
  g_rv_worker_adapter_deterministic_attempt_recovery_preserve_f9e86f59 -->|awaiting_verification| g_rv_worker_adapter_deterministic_attempt_verification_jump_0fedcb93
  g_rv_worker_adapter_deterministic_attempt_verification_jump_0fedcb93 -->|jump: independent evidence gate| g_rv_outcome_verifier_independent_result_verification_intake_faa4dd99
  g_rv_worker_adapter_deterministic_attempt_recovery_policy_13bb5685 -->|diagnostic_branch: effect class is retry_safe| g_rv_worker_adapter_deterministic_attempt_recovery_retry_cd947e91
  g_rv_worker_adapter_deterministic_attempt_recovery_policy_13bb5685 -->|diagnostic_branch: external or legacy outcome uncertain| g_rv_worker_adapter_deterministic_attempt_recovery_unknown_673fc7f3
  g_rv_worker_adapter_deterministic_attempt_recovery_retry_cd947e91 -->|fenced and requeued| g_rv_worker_adapter_deterministic_attempt_recovery_audit_fb03175c
  g_rv_worker_adapter_deterministic_attempt_recovery_unknown_673fc7f3 -->|no blind replay| g_rv_worker_adapter_deterministic_attempt_recovery_audit_fb03175c
  g_rv_worker_adapter_deterministic_attempt_recovery_audit_fb03175c -->|recovery_route: continue unrelated work| g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4
  g_rv_worker_adapter_deterministic_attempt_action_cef7346f -->|action output reaches durable attempt boundary| g_rv_worker_adapter_deterministic_attempt_begin_9ea07cfe
  g_rv_worker_adapter_deterministic_attempt_result_12aa9ef4 -->|durable result| g_rv_worker_adapter_deterministic_attempt_learning_83260d87
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

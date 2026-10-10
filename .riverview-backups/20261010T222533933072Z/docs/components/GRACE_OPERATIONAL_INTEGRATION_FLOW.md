# Grace Operational Integration

**Document Revision:** 1.0.4
**Status:** PLANNED — mandatory M4.4 deliverable; not implemented or operationally verified.
**Canonical source:** `process_graphs/grace/operational-integration.json` and `process_graphs/cme/progress-and-recovery.json`.
**Generation:** `python3 scripts/process_graph.py generate`; do not edit the Mermaid projection manually.

This planned flow registers the objective intake, authority binding, reasoning,
durable plan, assignment fanout, CME observation, artifact verification, follow-up,
and genuine Steward escalation required by M4.4. It is a design registration only.

Stable jump points connect Grace delegation to
`rv:worker-adapter:deterministic-attempt:continuous-cycle`, CME progress to
`rv:cme:progress-and-recovery:observe`, and CME attention feedback to
`rv:grace:operational-integration:evidence-review`.

```mermaid
flowchart LR
  subgraph g_rv_cme_progress_and_recovery["CME / progress-and-recovery.v1"]
    g_rv_cme_progress_and_recovery_monitor_start_3c5b8496(["Acquire the CME PostgreSQL advisory lease and begin repeated scans"])
    g_rv_cme_progress_and_recovery_observe_428defda["Read all nonterminal assignments, durable progress events, deadlines, and leases"]
    g_rv_cme_progress_and_recovery_stall_decision_e8a6e869{"Compare progress age and deadlines with explicit thresholds; preserve assignment isolation"}
    g_rv_cme_progress_and_recovery_attention_845fe834[["Append idempotent attention events for stalled, overdue, blocked, or waiting assignments"]]
    g_rv_cme_progress_and_recovery_recovery_22db97e3["Append one traceable recovery request for a stalled expired lease; CME does not execute it"]
    g_rv_cme_progress_and_recovery_resident_feedback_ff3dbee2["PLANNED — return progress and attention evidence to Grace"]
    g_rv_cme_progress_and_recovery_service_lock_cd8c9580{"Is this instance the sole holder of the CME service lease?"}
    g_rv_cme_progress_and_recovery_deadline_measurement_e28bd00c["Measure configured UTC deadline and durable progress age"]
    g_rv_cme_progress_and_recovery_worker_health_5dbdee95["Report workers healthy only from fresh unexpired lease heartbeats"]
    g_rv_cme_progress_and_recovery_monitor_failure_e312bec5[["Persist sanitized scan failure when PostgreSQL remains reachable"]]
    g_rv_cme_progress_and_recovery_retry_backoff_c0e76a05["Retry database observation with bounded exponential backoff"]
  end
  g_rv_grace_operational_integration_evidence_review_600fe7b4["Registered target<br/>rv:grace:operational-integration"]
  g_rv_cme_progress_and_recovery_monitor_start_3c5b8496 --> g_rv_cme_progress_and_recovery_service_lock_cd8c9580
  g_rv_cme_progress_and_recovery_service_lock_cd8c9580 -->|single active monitor instance| g_rv_cme_progress_and_recovery_observe_428defda
  g_rv_cme_progress_and_recovery_service_lock_cd8c9580 -->|diagnostic_branch: database unavailable or service lease held| g_rv_cme_progress_and_recovery_monitor_failure_e312bec5
  g_rv_cme_progress_and_recovery_observe_428defda --> g_rv_cme_progress_and_recovery_deadline_measurement_e28bd00c
  g_rv_cme_progress_and_recovery_deadline_measurement_e28bd00c --> g_rv_cme_progress_and_recovery_worker_health_5dbdee95
  g_rv_cme_progress_and_recovery_worker_health_5dbdee95 --> g_rv_cme_progress_and_recovery_stall_decision_e8a6e869
  g_rv_cme_progress_and_recovery_stall_decision_e8a6e869 -->|No overdue, stalled, blocked, or waiting condition; continue scan| g_rv_cme_progress_and_recovery_observe_428defda
  g_rv_cme_progress_and_recovery_stall_decision_e8a6e869 -->|escalation: Durable attention required| g_rv_cme_progress_and_recovery_attention_845fe834
  g_rv_cme_progress_and_recovery_stall_decision_e8a6e869 -->|diagnostic_branch: Query or persistence failure| g_rv_cme_progress_and_recovery_monitor_failure_e312bec5
  g_rv_cme_progress_and_recovery_attention_845fe834 -->|recovery_route: Stalled running assignment has expired lease| g_rv_cme_progress_and_recovery_recovery_22db97e3
  g_rv_cme_progress_and_recovery_attention_845fe834 -->|documentation: Future Grace integration reads authoritative attention events| g_rv_cme_progress_and_recovery_resident_feedback_ff3dbee2
  g_rv_cme_progress_and_recovery_resident_feedback_ff3dbee2 -->|jump| g_rv_grace_operational_integration_evidence_review_600fe7b4
  g_rv_cme_progress_and_recovery_recovery_22db97e3 -->|Request recorded; monitor continues unrelated work| g_rv_cme_progress_and_recovery_observe_428defda
  g_rv_cme_progress_and_recovery_monitor_failure_e312bec5 -->|recovery_route| g_rv_cme_progress_and_recovery_retry_backoff_c0e76a05
  g_rv_cme_progress_and_recovery_retry_backoff_c0e76a05 -->|recovery_route: Reacquire service lease and rescan durable state| g_rv_cme_progress_and_recovery_monitor_start_3c5b8496
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

## CME progress and recovery view

```mermaid
flowchart LR
  subgraph g_rv_grace_operational_integration["RESIDENT-ORCHESTRATION / grace-engineering-objective.v1"]
    g_rv_grace_operational_integration_objective_intake_55567c14(["PLANNED — receive and durably record Steward objective and authority"])
    g_rv_grace_operational_integration_authority_check_71ce44bf["PLANNED — bind objective to delegated office authority and acceptance criteria"]
    g_rv_grace_operational_integration_reason_decompose_d48619ca["PLANNED — reason about objective and decompose durable engineering plan"]
    g_rv_grace_operational_integration_durable_plan_26bc431c["PLANNED — persist and revise plan across context and model replacement"]
    g_rv_grace_operational_integration_assignment_fanout_81ca8043["PLANNED — create multiple independently schedulable assignments"]
    g_rv_grace_operational_integration_worker_dispatch_20506b72["PLANNED — delegate through CME to replaceable real engineering executors"]
    g_rv_grace_operational_integration_cme_progress_68f6775b["PLANNED — subscribe to durable progress, stall, and recovery events from CME"]
    g_rv_grace_operational_integration_evidence_review_600fe7b4["PLANNED — interpret execution and independent verification evidence"]
    g_rv_grace_operational_integration_verification_feedback_3d572dc6["PLANNED — consume independent verifier decision and evidence"]
    g_rv_grace_operational_integration_objective_check_1e4d916a{"PLANNED — determine whether objective acceptance criteria are independently met"}
    g_rv_grace_operational_integration_replan_58351ccd["PLANNED — revise plan and initiate follow-up work after evidence or failure"]
    g_rv_grace_operational_integration_steward_escalation_ca57acbb[["PLANNED — request only genuine Steward decision or authority"]]
    g_rv_grace_operational_integration_objective_complete_a6f22d23(["PLANNED — objective closed only with independently verified evidence"])
  end
  g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4["Registered target<br/>rv:worker-adapter:deterministic-attempt"]
  g_rv_cme_progress_and_recovery_observe_428defda["Registered target<br/>rv:cme:progress-and-recovery"]
  g_rv_outcome_verifier_independent_result_decision_5500806a["Registered target<br/>rv:outcome-verifier:independent-result"]
  g_rv_grace_operational_integration_objective_intake_55567c14 --> g_rv_grace_operational_integration_authority_check_71ce44bf
  g_rv_grace_operational_integration_authority_check_71ce44bf --> g_rv_grace_operational_integration_reason_decompose_d48619ca
  g_rv_grace_operational_integration_reason_decompose_d48619ca --> g_rv_grace_operational_integration_durable_plan_26bc431c
  g_rv_grace_operational_integration_durable_plan_26bc431c --> g_rv_grace_operational_integration_assignment_fanout_81ca8043
  g_rv_grace_operational_integration_assignment_fanout_81ca8043 --> g_rv_grace_operational_integration_worker_dispatch_20506b72
  g_rv_grace_operational_integration_worker_dispatch_20506b72 -->|jump| g_rv_worker_adapter_deterministic_attempt_continuous_cycle_b746f9c4
  g_rv_grace_operational_integration_assignment_fanout_81ca8043 --> g_rv_grace_operational_integration_cme_progress_68f6775b
  g_rv_grace_operational_integration_cme_progress_68f6775b -->|jump| g_rv_cme_progress_and_recovery_observe_428defda
  g_rv_grace_operational_integration_evidence_review_600fe7b4 --> g_rv_grace_operational_integration_objective_check_1e4d916a
  g_rv_grace_operational_integration_evidence_review_600fe7b4 --> g_rv_grace_operational_integration_verification_feedback_3d572dc6
  g_rv_grace_operational_integration_verification_feedback_3d572dc6 -->|jump| g_rv_outcome_verifier_independent_result_decision_5500806a
  g_rv_grace_operational_integration_objective_check_1e4d916a -->|verification: PLANNED — all criteria independently verified| g_rv_grace_operational_integration_objective_complete_a6f22d23
  g_rv_grace_operational_integration_objective_check_1e4d916a -->|recovery_route: PLANNED — unmet criteria or new evidence| g_rv_grace_operational_integration_replan_58351ccd
  g_rv_grace_operational_integration_objective_check_1e4d916a -->|escalation: PLANNED — genuine decision required| g_rv_grace_operational_integration_steward_escalation_ca57acbb
  g_rv_grace_operational_integration_replan_58351ccd --> g_rv_grace_operational_integration_durable_plan_26bc431c
  g_rv_grace_operational_integration_steward_escalation_ca57acbb -->|PLANNED — resume after recorded decision| g_rv_grace_operational_integration_durable_plan_26bc431c
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

Revision history: 1.0.0 — initial planned M4.4 view; canonical views are generated.

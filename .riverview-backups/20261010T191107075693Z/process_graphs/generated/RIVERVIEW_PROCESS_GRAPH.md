# Riverview aggregate process graph

**Document Revision:** 1.0.9  
**Generated from:** canonical workflow JSON; do not edit this projection by hand.  
**Source:** `python3 scripts/process_graph.py generate`  

The graph is complete across registered workflows. Use focused component flow documents for detailed reading. Unimplemented roadmap integration points are explicitly labeled planned.

```mermaid
flowchart LR
  g_rv_assignment_scheduler_independent_claims_88bd80c4[["ASSIGNMENT-SCHEDULER<br/>independent-assignment-claims.v1<br/>rv:assignment-scheduler:independent-claims"]]
  g_rv_cme_progress_and_recovery_402efffa[["CME<br/>progress-and-recovery.v1<br/>rv:cme:progress-and-recovery"]]
  g_rv_event_processor_assignment_progression_fa10db2d[["EVENT-PROCESSOR<br/>assignment-progression.v1<br/>rv:event-processor:assignment-progression"]]
  g_rv_grace_operational_integration_9989f0be[["RESIDENT-ORCHESTRATION<br/>grace-engineering-objective.v1<br/>rv:grace:operational-integration"]]
  g_rv_outcome_verifier_independent_result_1d5c0875[["OUTCOME-VERIFIER<br/>deterministic-result-verification.v1<br/>rv:outcome-verifier:independent-result"]]
  g_rv_postgres_ledger_assignment_lifecycle_a9a01b67[["POSTGRES-LEDGER<br/>assignment-lifecycle.v1<br/>rv:postgres-ledger:assignment-lifecycle"]]
  g_rv_postgres_ledger_migration_4c89ef23[["POSTGRES-LEDGER<br/>postgres-migration.v1<br/>rv:postgres-ledger:migration"]]
  g_rv_runtime_baseline_commissioning_46ff1ccf[["RUNTIME-BASELINE<br/>runtime-baseline.v1<br/>rv:runtime-baseline:commissioning"]]
  g_rv_steward_dashboard_status_75f7c259[["STEWARD-DASHBOARD<br/>status-projection.v1<br/>rv:steward-dashboard:status"]]
  g_rv_worker_adapter_deterministic_attempt_15d59b6f[["WORKER-ADAPTER<br/>deterministic-attempt.v1<br/>rv:worker-adapter:deterministic-attempt"]]
  g_rv_assignment_scheduler_independent_claims_88bd80c4 -->|jump: Open the M1.3 ready-state producer workflow| g_rv_event_processor_assignment_progression_fa10db2d
  g_rv_cme_progress_and_recovery_402efffa -->|jump| g_rv_grace_operational_integration_9989f0be
  g_rv_event_processor_assignment_progression_fa10db2d -->|prerequisite: M1.2 migrated ledger schema; not a runtime call| g_rv_postgres_ledger_migration_4c89ef23
  g_rv_event_processor_assignment_progression_fa10db2d -->|jump| g_rv_runtime_baseline_commissioning_46ff1ccf
  g_rv_grace_operational_integration_9989f0be -->|jump| g_rv_worker_adapter_deterministic_attempt_15d59b6f
  g_rv_grace_operational_integration_9989f0be -->|jump| g_rv_cme_progress_and_recovery_402efffa
  g_rv_grace_operational_integration_9989f0be -->|jump| g_rv_outcome_verifier_independent_result_1d5c0875
  g_rv_outcome_verifier_independent_result_1d5c0875 -->|jump| g_rv_worker_adapter_deterministic_attempt_15d59b6f
  g_rv_postgres_ledger_migration_4c89ef23 -->|jump| g_rv_steward_dashboard_status_75f7c259
  g_rv_runtime_baseline_commissioning_46ff1ccf -->|jump| g_rv_postgres_ledger_migration_4c89ef23
  g_rv_worker_adapter_deterministic_attempt_15d59b6f -->|jump: Follow current M1.4 lease validation| g_rv_assignment_scheduler_independent_claims_88bd80c4
  g_rv_worker_adapter_deterministic_attempt_15d59b6f -->|prerequisite: M1.4 lease table/token contract; not a runtime call| g_rv_assignment_scheduler_independent_claims_88bd80c4
  g_rv_worker_adapter_deterministic_attempt_15d59b6f -->|jump: independent evidence gate| g_rv_outcome_verifier_independent_result_1d5c0875
```

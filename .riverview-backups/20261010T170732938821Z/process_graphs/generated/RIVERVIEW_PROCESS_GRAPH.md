# Riverview aggregate process graph

**Document Revision:** 1.0.3  
**Generated from:** canonical workflow JSON; do not edit this projection by hand.  
**Source:** `python3 scripts/process_graph.py generate`  

The graph is complete across registered workflows. Use focused component flow documents for detailed reading. Unimplemented roadmap integration points are explicitly labeled planned.

```mermaid
flowchart LR
  g_rv_event_processor_assignment_progression_fa10db2d[["EVENT-PROCESSOR<br/>assignment-progression.v1<br/>rv:event-processor:assignment-progression"]]
  g_rv_postgres_ledger_assignment_lifecycle_a9a01b67[["POSTGRES-LEDGER<br/>assignment-lifecycle.v1<br/>rv:postgres-ledger:assignment-lifecycle"]]
  g_rv_postgres_ledger_migration_4c89ef23[["POSTGRES-LEDGER<br/>postgres-migration.v1<br/>rv:postgres-ledger:migration"]]
  g_rv_runtime_baseline_commissioning_46ff1ccf[["RUNTIME-BASELINE<br/>runtime-baseline.v1<br/>rv:runtime-baseline:commissioning"]]
  g_rv_steward_dashboard_status_75f7c259[["STEWARD-DASHBOARD<br/>status-projection.v1<br/>rv:steward-dashboard:status"]]
  g_rv_event_processor_assignment_progression_fa10db2d -->|prerequisite: M1.2 migrated ledger schema; not a runtime call| g_rv_postgres_ledger_migration_4c89ef23
  g_rv_event_processor_assignment_progression_fa10db2d -->|jump| g_rv_runtime_baseline_commissioning_46ff1ccf
  g_rv_postgres_ledger_migration_4c89ef23 -->|jump| g_rv_steward_dashboard_status_75f7c259
  g_rv_runtime_baseline_commissioning_46ff1ccf -->|jump| g_rv_postgres_ledger_migration_4c89ef23
```

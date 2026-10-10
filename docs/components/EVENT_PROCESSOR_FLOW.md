# Riverview~ event processor flow

**Document Revision:** 1.0.3  
**Component:** EVENT-PROCESSOR  
**Task:** RV-M1.3-001  
**Workflow:** assignment-progression.v1  
**Canonical source:** `process_graphs/event-processor/assignment-progression.json`

```mermaid
flowchart LR
  subgraph g_rv_event_processor_assignment_progression["EVENT-PROCESSOR / assignment-progression.v1"]
    g_rv_event_processor_assignment_progression_start_18a7f5d0(["Supervised event processor starts"])
    g_rv_event_processor_assignment_progression_lease_93ecb69d["Acquire PostgreSQL advisory leadership lock for this consumer"]
    g_rv_event_processor_assignment_progression_lock_failure_13f1aa29[["Another instance holds consumer lease; refuse duplicate runner"]]
    g_rv_event_processor_assignment_progression_read_cursor_799d2c85["Read durable per-consumer event cursor"]
    g_rv_event_processor_assignment_progression_fetch_0df7d2f1["Fetch commit-ordered events after the durable cursor"]
    g_rv_event_processor_assignment_progression_created_8baea8e6{"Event is assignment.created?"}
    g_rv_event_processor_assignment_progression_queued_85118434{"Assignment still queued?"}
    g_rv_event_processor_assignment_progression_advance_b0fce628["Idempotently transition assignment to ready"]
    g_rv_event_processor_assignment_progression_skip_2d688fb5["Ignore unrelated or already advanced event"]
    g_rv_event_processor_assignment_progression_checkpoint_f5208633["Persist cursor only after successful handling"]
    g_rv_event_processor_assignment_progression_retry_5006f270["Bounded backoff; reconnect to PostgreSQL and reacquire leadership"]
    g_rv_event_processor_assignment_progression_replay_25ce5700["Restart replays uncheckpointed source event safely"]
    g_rv_event_processor_assignment_progression_stop_8345a53a(["SIGTERM checkpointed stop and leadership release"])
    g_rv_event_processor_assignment_progression_startup_preflight_86f3cffb["Validate credential delivery and source-matched migration history"]
    g_rv_event_processor_assignment_progression_preflight_failure_859a43e9[["Refuse event consumption on unsafe credential or schema mismatch"]]
    g_rv_event_processor_assignment_progression_baseline_jump_a48969e4["M1.1 runtime credential and host commissioning baseline"]
  end
  g_rv_postgres_ledger_migration_require_schema_7fdaca28["Registered target<br/>rv:postgres-ledger:migration"]
  g_rv_runtime_baseline_commissioning_ready_1e7806fe["Registered target<br/>rv:runtime-baseline:commissioning"]
  g_rv_event_processor_assignment_progression_lease_93ecb69d -->|diagnostic_branch: Lock unavailable| g_rv_event_processor_assignment_progression_lock_failure_13f1aa29
  g_rv_event_processor_assignment_progression_lease_93ecb69d -->|Acquired| g_rv_event_processor_assignment_progression_read_cursor_799d2c85
  g_rv_event_processor_assignment_progression_read_cursor_799d2c85 --> g_rv_event_processor_assignment_progression_fetch_0df7d2f1
  g_rv_event_processor_assignment_progression_fetch_0df7d2f1 --> g_rv_event_processor_assignment_progression_created_8baea8e6
  g_rv_event_processor_assignment_progression_created_8baea8e6 -->|Yes| g_rv_event_processor_assignment_progression_queued_85118434
  g_rv_event_processor_assignment_progression_created_8baea8e6 -->|No| g_rv_event_processor_assignment_progression_skip_2d688fb5
  g_rv_event_processor_assignment_progression_queued_85118434 -->|Yes| g_rv_event_processor_assignment_progression_advance_b0fce628
  g_rv_event_processor_assignment_progression_queued_85118434 -->|No| g_rv_event_processor_assignment_progression_skip_2d688fb5
  g_rv_event_processor_assignment_progression_advance_b0fce628 --> g_rv_event_processor_assignment_progression_checkpoint_f5208633
  g_rv_event_processor_assignment_progression_skip_2d688fb5 --> g_rv_event_processor_assignment_progression_checkpoint_f5208633
  g_rv_event_processor_assignment_progression_checkpoint_f5208633 -->|Next poll| g_rv_event_processor_assignment_progression_read_cursor_799d2c85
  g_rv_event_processor_assignment_progression_read_cursor_799d2c85 -->|diagnostic_branch: Database or handler error| g_rv_event_processor_assignment_progression_retry_5006f270
  g_rv_event_processor_assignment_progression_retry_5006f270 -->|recovery_route| g_rv_event_processor_assignment_progression_replay_25ce5700
  g_rv_event_processor_assignment_progression_replay_25ce5700 -->|recovery_route| g_rv_event_processor_assignment_progression_read_cursor_799d2c85
  g_rv_event_processor_assignment_progression_checkpoint_f5208633 -->|SIGTERM| g_rv_event_processor_assignment_progression_stop_8345a53a
  g_rv_event_processor_assignment_progression_lease_93ecb69d -->|prerequisite: M1.2 migrated ledger schema; not a runtime call| g_rv_postgres_ledger_migration_require_schema_7fdaca28
  g_rv_event_processor_assignment_progression_start_18a7f5d0 --> g_rv_event_processor_assignment_progression_startup_preflight_86f3cffb
  g_rv_event_processor_assignment_progression_startup_preflight_86f3cffb -->|diagnostic_branch: Credential or migration contract invalid| g_rv_event_processor_assignment_progression_preflight_failure_859a43e9
  g_rv_event_processor_assignment_progression_startup_preflight_86f3cffb -->|Validated| g_rv_event_processor_assignment_progression_lease_93ecb69d
  g_rv_event_processor_assignment_progression_startup_preflight_86f3cffb -->|prerequisite: M1.1 host and credential contract; not a runtime call| g_rv_event_processor_assignment_progression_baseline_jump_a48969e4
  g_rv_event_processor_assignment_progression_baseline_jump_a48969e4 -->|jump| g_rv_runtime_baseline_commissioning_ready_1e7806fe
  g_rv_event_processor_assignment_progression_retry_5006f270 -->|recovery_route: Database returned; verify source schema and reacquire the consumer lock| g_rv_event_processor_assignment_progression_lease_93ecb69d
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

This Mermaid view is generated with `python3 scripts/process_graph.py generate`.
The canonical JSON is authoritative. Use
`python3 scripts/process_graph.py check` to detect stale output.

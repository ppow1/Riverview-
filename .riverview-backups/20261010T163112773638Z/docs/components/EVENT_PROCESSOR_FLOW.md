# Riverview~ event processor flow

**Document Revision:** 1.0.1  
**Component:** EVENT-PROCESSOR  
**Task:** RV-M1.3-001  
**Workflow:** assignment-progression.v1  
**Canonical source:** `process_graphs/event-processor/assignment-progression.json`

```mermaid
flowchart LR
  subgraph g_rv_event_processor_assignment_progression["EVENT-PROCESSOR / assignment-progression.v1"]
    n0(["Supervised event processor starts<br/>rv:event-processor:assignment-progression:start"])
    n1["Acquire PostgreSQL advisory leadership lock for this consumer<br/>rv:event-processor:assignment-progression:lease"]
    n2[["Another instance holds consumer lease; refuse duplicate runner<br/>rv:event-processor:assignment-progression:lock-failure"]]
    n3["Read durable per-consumer event cursor<br/>rv:event-processor:assignment-progression:read-cursor"]
    n4["Fetch ordered committed events after cursor<br/>rv:event-processor:assignment-progression:fetch"]
    n5{"Event is assignment.created?<br/>rv:event-processor:assignment-progression:created"}
    n6{"Assignment still queued?<br/>rv:event-processor:assignment-progression:queued"}
    n7["Idempotently transition assignment to ready<br/>rv:event-processor:assignment-progression:advance"]
    n8["Ignore unrelated or already advanced event<br/>rv:event-processor:assignment-progression:skip"]
    n9["Persist cursor only after successful handling<br/>rv:event-processor:assignment-progression:checkpoint"]
    n10["Log failure type and retry with bounded backoff<br/>rv:event-processor:assignment-progression:retry"]
    n11["Restart replays uncheckpointed source event safely<br/>rv:event-processor:assignment-progression:replay"]
    n12(["SIGTERM checkpointed stop and leadership release<br/>rv:event-processor:assignment-progression:stop"])
  end
  n13["External graph target<br/>rv:postgres-ledger:migration:require-schema"]
  n0 --> n1
  n1 -->|diagnostic_branch: Lock unavailable| n2
  n1 -->|Acquired| n3
  n3 --> n4
  n4 --> n5
  n5 -->|Yes| n6
  n5 -->|No| n8
  n6 -->|Yes| n7
  n6 -->|No| n8
  n7 --> n9
  n8 --> n9
  n9 -->|Next poll| n3
  n3 -->|diagnostic_branch: Database or handler error| n10
  n10 -->|recovery_route| n11
  n11 -->|recovery_route| n3
  n9 -->|SIGTERM| n12
  n1 -->|prerequisite: M1.2 migrated ledger schema; not a runtime call| n13
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

This Mermaid view is generated with `python3 scripts/process_graph.py generate`.
The canonical JSON is authoritative. Use
`python3 scripts/process_graph.py check` to detect stale output.

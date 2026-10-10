<!--
Riverview~ Controlled Document
File: docs/components/POSTGRES_LEDGER_FLOW.md
Revision: 1.0.1
Migration: ENG-REV-002
-->
# PostgreSQL ledger — component flow and Steward projection

## Transaction flow
```mermaid
flowchart LR
  subgraph g_rv_postgres_ledger_migration["POSTGRES-LEDGER / postgres-migration.v1"]
    n0["Confirm live host, database, schema owner/access, empty target and compatibility<br/>rv:postgres-ledger:migration:preflight"]
    n1{"Preflight safe to proceed?<br/>rv:postgres-ledger:migration:preflight-clear"}
    n2[["Stop on identity, compatibility or safety mismatch<br/>rv:postgres-ledger:migration:stop"]]
    n3["Protected full database backup; checksum and restore drill<br/>rv:postgres-ledger:migration:backup"]
    n4["Recoverable backup independently restored and verified<br/>rv:postgres-ledger:migration:backup-verified"]
    n5(["Explicit migration request for selected schema<br/>rv:postgres-ledger:migration:apply"])
    n6{"Stored checksum matches source?<br/>rv:postgres-ledger:migration:check"}
    n7[["Checksum mismatch; stop without schema changes<br/>rv:postgres-ledger:migration:drift"]]
    n8["Identical applied migration is a no-op<br/>rv:postgres-ledger:migration:noop"]
    n9["Apply versioned SQL and checksum atomically<br/>rv:postgres-ledger:migration:sql"]
    n10["PostgresLedger requires migrated target schema<br/>rv:postgres-ledger:migration:require-schema"]
    n11["Caller requests assignment create or transition<br/>rv:postgres-ledger:migration:caller"]
    n12["Begin PostgreSQL transaction<br/>rv:postgres-ledger:migration:transaction"]
    n13["Advisory lock on idempotency key<br/>rv:postgres-ledger:migration:lock"]
    n14{"Existing event key?<br/>rv:postgres-ledger:migration:key-exists"}
    n15["Exact semantic replay returns current assignment<br/>rv:postgres-ledger:migration:replay"]
    n16[["Conflicting key reuse is rejected<br/>rv:postgres-ledger:migration:collision"]]
    n17{"Create or transition?<br/>rv:postgres-ledger:migration:operation"}
    n18["Insert assignment metadata<br/>rv:postgres-ledger:migration:create"]
    n19["Lock assignment row FOR UPDATE<br/>rv:postgres-ledger:migration:row-lock"]
    n20{"Legal state transition?<br/>rv:postgres-ledger:migration:legal"}
    n21[["Reject illegal transition<br/>rv:postgres-ledger:migration:illegal"]]
    n22["Update state and workflow step<br/>rv:postgres-ledger:migration:update"]
    n23["Append event with authority and causality<br/>rv:postgres-ledger:migration:event"]
    n24["Commit assignment and event atomically<br/>rv:postgres-ledger:migration:commit"]
    n25["Read assignment and ordered events<br/>rv:postgres-ledger:migration:read"]
    n26["On-demand status snapshot<br/>rv:postgres-ledger:migration:snapshot"]
    n27["M3.1 live dashboard (planned; not implemented)<br/>rv:postgres-ledger:migration:dashboard-jump"]
  end
  n28["External graph target<br/>rv:steward-dashboard:status:ingest"]
  n0 -->|verification| n1
  n1 -->|diagnostic_branch: No| n2
  n1 -->|Yes| n3
  n3 -->|verification| n4
  n4 --> n5
  n5 --> n6
  n6 -->|diagnostic_branch: Mismatch| n7
  n6 -->|Already applied, identical| n8
  n6 -->|New version| n9
  n8 --> n10
  n9 --> n10
  n10 -->|prerequisite: Verified schema contract; not a runtime call| n11
  n11 --> n12
  n12 --> n13
  n13 --> n14
  n14 -->|Exact replay| n15
  n14 -->|diagnostic_branch: Conflict| n16
  n14 -->|New key| n17
  n17 -->|Create| n18
  n17 -->|Transition| n19
  n19 --> n20
  n20 -->|diagnostic_branch: No| n21
  n20 -->|Yes| n22
  n18 --> n23
  n22 --> n23
  n23 --> n24
  n24 --> n25
  n15 --> n25
  n25 --> n26
  n26 --> n27
  n27 -->|jump| n28
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

## Assignment lifecycle
```mermaid
flowchart LR
  subgraph g_rv_postgres_ledger_assignment_lifecycle["POSTGRES-LEDGER / assignment-lifecycle.v1"]
    n0(["Assignment intake<br/>rv:postgres-ledger:assignment-lifecycle:intake"])
    n1["queued<br/>rv:postgres-ledger:assignment-lifecycle:queued"]
    n2["ready<br/>rv:postgres-ledger:assignment-lifecycle:ready"]
    n3["running<br/>rv:postgres-ledger:assignment-lifecycle:running"]
    n4["awaiting_verification<br/>rv:postgres-ledger:assignment-lifecycle:awaiting-verification"]
    n5["rework_required<br/>rv:postgres-ledger:assignment-lifecycle:rework"]
    n6[["blocked<br/>rv:postgres-ledger:assignment-lifecycle:blocked"]]
    n7[["awaiting_steward<br/>rv:postgres-ledger:assignment-lifecycle:awaiting-steward"]]
    n8(["completed (caller verification flag is only a claim)<br/>rv:postgres-ledger:assignment-lifecycle:completed"])
    n9(["cancelled<br/>rv:postgres-ledger:assignment-lifecycle:cancelled"])
  end
  n0 --> n1
  n1 --> n2
  n1 --> n6
  n1 --> n9
  n2 --> n3
  n2 --> n6
  n2 --> n9
  n3 --> n4
  n3 --> n6
  n3 --> n7
  n4 -->|verified claim required; not independent proof| n8
  n4 --> n5
  n4 --> n6
  n5 --> n2
  n5 --> n6
  n5 --> n9
  n6 --> n2
  n6 --> n9
  n6 --> n7
  n7 --> n2
  n7 --> n9
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

## Steward view — delivered versus planned
| Signal | On-demand snapshot | Live Steward view |
| --- | --- | --- |
| PostgreSQL connectivity | Yes | Not built |
| Assignment counts by state | Yes, if tables initialized | Not built |
| Last event sequence and timestamp | Yes, if tables initialized | Not built |
| Database health and failures over time | Single-point read only | Not built |
| Alerts, CME recovery, drill-down, authorization | No | Not built |

Use `scripts/postgres_ledger_steward_snapshot.py` to generate a read-only JSON status snapshot. It accepts `RIVERVIEW_PG_DSN` and `RIVERVIEW_PG_SCHEMA`. It never initializes tables, writes data, or starts a web service. If tables do not exist, it reports `not_initialized` rather than creating them.

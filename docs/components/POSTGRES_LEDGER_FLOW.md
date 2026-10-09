# PostgreSQL ledger — component flow and Steward projection

## Transaction flow
```mermaid
flowchart TD
 A[Caller: create or transition] --> B[PostgresLedger]
 B --> C[Begin PostgreSQL transaction]
 C --> D[Advisory lock on idempotency key]
 D --> E{Existing event key?}
 E -->|Matching replay| F[Return current assignment]
 E -->|Conflicting replay| X[Reject / rollback]
 E -->|New| G{Create or transition?}
 G -->|Create| H[Reject existing ID / insert queued assignment]
 G -->|Transition| I[Lock assignment row FOR UPDATE]
 I --> J{Legal state transition?}
 J -->|No| X
 J -->|Yes| K{Completing?}
 K -->|Yes, verified flag false| X
 K -->|No or flag true| L[Update assignment and version]
 H --> M[Insert event in same transaction]
 L --> M
 M --> N[Commit]
 N --> O[Read assignment / ordered events]
 F --> O
 O --> P[On-demand Steward snapshot]
 P -. future .-> Q[Live Steward dashboard + alerts]
```

## Assignment lifecycle
```mermaid
stateDiagram-v2
 [*] --> queued
 queued --> ready
 queued --> blocked
 queued --> cancelled
 ready --> running
 ready --> blocked
 ready --> cancelled
 running --> awaiting_verification
 running --> blocked
 running --> awaiting_steward
 awaiting_verification --> completed: verified flag (not independent proof)
 awaiting_verification --> rework_required
 awaiting_verification --> blocked
 rework_required --> ready
 rework_required --> blocked
 rework_required --> cancelled
 blocked --> ready
 blocked --> cancelled
 blocked --> awaiting_steward
 awaiting_steward --> ready
 awaiting_steward --> cancelled
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

# Riverview~ runtime baseline process map

**Document Revision:** 1.0.1
**Component:** RUNTIME-BASELINE
**Repair task:** RV-M1.1-002
**Workflow:** runtime-baseline.v1
**Task:** RV-M1.1-001
**Status:** implemented diagnostic flow; Camrui execution NOT VERIFIED

```mermaid
flowchart TD
  P[Authorized one-time commissioning] --> F{package_bytes: checksum and LF-only shells?}
  F -- No --> X[Preserve failed package; rebuild corrected source]
  X --> F
  F -- Yes --> C[Preserve unit and prior release; install credential source]
  C --> S[systemd starts unprivileged probe and supplies credential]
  S --> identity{identity: correct non-login account?}
  identity -- No --> B[blocked: accountable configuration error]
  identity -- Yes --> storage{storage: private owned directory?}
  storage -- No --> B
  storage -- Yes --> credential{credential: safe readable file and no override?}
  credential -- No --> B
  credential -- Yes --> database{database: read-only TCP and least-privilege role?}
  database -- Unreachable --> U[unavailable: dependency interruption]
  database -- Wrong identity or privilege --> B
  database -- Yes --> schema{schema: riverview_dev ownership and access?}
  schema -- No --> B
  schema -- Yes --> ready[ready: baseline verified; institution NOT VERIFIED]
  B --> R[Authorized diagnosis and repair from cookbook]
  U --> R
  R --> S
  ready --> O[Independent observer checks revision and timestamp]
  O -- Expired --> T[stale; not ready]
  O -- Missing or invalid --> U
  O -- Fresh --> E[Preserve acceptance report from two distinct invocations]
  T --> S
  E --> A{Steward accepts and resolves sequencing?}
  A -- No --> H[Record acceptance hold; remain at M1.1]
  A -- Yes --> N[Next engineering step M1.2]
  R -- Bad deployment --> K[Restore verified unit and release predecessor]
  K --> S
```

`package_bytes` is an engineering preflight reported by rv.package-verification.v1,
not an institutional workflow event. It checks both scripts before host mutation.

Stable probe step IDs `identity`, `storage`, `credential`, `database`, `schema`,
`ready` are emitted in JSON on failure/success and map directly to the
[cookbook](RUNTIME_BASELINE_COOKBOOK.md). The database/schema subchecks are
read-only; no assignment events, recovery authority, worker or CME loops are
claimed here. Notifications are operator-visible exit codes/reports; automated
durable notification remains M3.2. The acceptance hold governs engineering
sequencing, not ongoing authorized institutional execution.

Restart means a new systemd diagnostic invocation and fresh credential delivery;
the latest report is replaced and immutable acceptance artifacts remain retained.

## Revision history

- 1.0.1: Add actual archive-byte preflight and failed-package rebuild path; preserved predecessor under docs/history/RV-M1.1-002/rev1.0.0.
- 1.0.0: Initial flow with errors, repeat invocation, rollback and acceptance hold.

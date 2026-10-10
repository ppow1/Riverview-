# Riverview~ runtime baseline process map

**Document Revision:** 1.0.5
**Component:** RUNTIME-BASELINE
**Repair task:** RV-M1.1-011
**Workflow:** runtime-baseline.v1
**Task:** RV-M1.1-001
**Status:** credential and loopback identity corrections implemented; live acceptance in progress

```mermaid
flowchart TD
  P[Committed source revision] --> P0[Build and verify package]
  P0 --> F{archive hash, commit, manifest and safe members valid?}
  F -- No --> X[Preserve failed package; rebuild corrected source]
  X --> F
  F -- Yes --> C[Extract verified archive into root-owned non-writable staging]
  C --> M[Preserve unit and prior release; run fixed installer]
  M --> G{Credential source exists?}
  G -- No --> T[Prompt on controlling TTY with echo disabled; create passfile exclusively]
  T -- TTY failure --> Q[Fail closed; passfile remains absent; retain partial release]
  Q --> R[Retry corrected installer after read-only ownership checks]
  R --> C
  G -- Yes --> S[systemd starts unprivileged probe and supplies root-owned credential]
  S --> CP[Validate source; exclusive no-follow copy to private mode-0600 runtime passfile]
  T -- Captured --> S
  CP --> identity{identity: correct non-login account?}
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
  R -- Bad deployment --> K[Rollback script validates and restores exact predecessor record]
  K --> S
```

Package verification checks the exact archive digest, source commit, checksum
manifest, Linux shell compatibility, and safe archive members before host
installation. Camrui's owner-authorized administrator performs the local
deployment; no project privilege broker is installed.

Stable probe step IDs `identity`, `storage`, `credential`, `database`, `schema`,
`ready` are emitted in JSON on failure/success and map directly to the
[cookbook](RUNTIME_BASELINE_COOKBOOK.md). The database/schema subchecks are
read-only; no assignment events, recovery authority, worker or CME loops are
claimed here. Notifications are operator-visible exit codes/reports; automated
durable notification remains M3.2. The acceptance hold governs engineering
sequencing, not ongoing authorized institutional execution. PID 1's root-owned
read-only credential mount is validated separately from runtime-owned state,
then copied to a private ephemeral mode-0600 file because libpq rejects mode
0440. systemd cleans that runtime directory after the oneshot stops.

Restart means a new systemd diagnostic invocation and fresh credential delivery;
the latest report is replaced and immutable acceptance artifacts remain retained.

## Revision history

- 1.0.3: Add hash-pinned broker flow and corrected systemd credential ownership contract; predecessor `.riverview-backups/20261010T142904684465Z/docs/components/RUNTIME_BASELINE_FLOW.md`.
- 1.0.4: Add private runtime passfile copy required by libpq; predecessor is recorded under RV-M1.1-010 in `.riverview-backups/manifest.jsonl`.
- 1.0.5: Retire the broker flow and record the corrected PostgreSQL inet host check; predecessor recorded under RV-M1.1-011.

- 1.0.2: Add hidden-TTY credential capture and safe retained-release retry branches; predecessor under docs/history/RV-M1.1-007/rev1.0.1/docs/components/RUNTIME_BASELINE_FLOW.md.

- 1.0.1: Add actual archive-byte preflight and failed-package rebuild path; preserved predecessor under docs/history/RV-M1.1-002/rev1.0.0.
- 1.0.0: Initial flow with errors, repeat invocation, rollback and acceptance hold.

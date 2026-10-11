<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/M4.1-DB-BOUNDARY/20261011T081700Z-live-bootstrap/checkout.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Record live M4.1 authority boundary and initial Steward bootstrap on Camrui
Authority: Steward-owned development database; additive authority schema only
Source: 4276af8a8296b9c3042076a78881b2ec6d9b766e (bootstrap); d3a0ed4fdec3061923964451ce2fccff18fadca7 (boundary apply)
History: artifacts.json SHA-256 manifest
-->
# M4.1 live authority bootstrap commissioning

## Deployment provenance and recovery

The protected backup
`/var/lib/postgresql/backups/riverview/m4.1/rv-m41-fk-20261011T080500Z/riverview.dump`
was verified (SHA-256 `60ce7aa35c95871c510098b28126f6a738f63f1efde773bf9ad0a96e6f164444`,
postgres:postgres 0600, `pg_restore --list` passes). It restored to unique
database `rv_restore_m41_fk_20261011t080500z`; counts matched: 9 Core
migrations, 4 assignments, 11 Core events, and 10 authority relations
(including the migration ledger). The exact disposable DB was verified idle
and dropped; its remaining catalog count is zero. No restore touched the live
application schema.

The M4.1 boundary correction was applied from a root-owned archive of
`d3a0ed4fdec3061923964451ce2fccff18fadca7`. Preflight correctly required
repair, apply returned `APPLIED`, and subsequent preflight returned
`PREFLIGHT_PASS` with `apply_required=false`. It grants `USAGE` to the protected
table owner for PostgreSQL FK checks; owner `CREATE` remains false.

The one-time root-only helper from root-owned commit
`4276af8a8296b9c3042076a78881b2ec6d9b766e` was then run. It returned
`BOOTSTRAPPED`; a new process returned `ALREADY_BOOTSTRAPPED`. The protected
token file is root:root 0600, 44 bytes. Its contents were never printed or
copied to evidence. An independent process checked the token's SHA-256 against
the active DB credential and returned only a match count.

## Observed live results

- Active Steward identities: **1** (`steward:camrui`).
- Active matching credential digest: **1**; stored value is SHA-256 only.
- Active grants: exactly `authority.grant:institution`,
  `identity.manage:institution`, `office.manage:institution`.
- Append-only `steward_bootstrapped` events: **1**.
- Runtime `riverview_core` schema USAGE: **false**; direct SELECT denied.
- Manager schema CREATE: **false**; owner membership: **false**; attempted
  CREATE denied; no probe relation was created.
- Core data baseline after bootstrap: migrations **9**, assignments **4**,
  events **11**.
- PostgreSQL, event processor, CME monitor, notification dispatcher,
  dashboard, and SSH: **active**.

Captured redacted outputs are in `preflight.txt`, `bootstrap-restart.txt`,
`token-file-metadata.txt`, `independent-credential-check.txt`,
`access-denials.txt`, `authority-and-core-state.txt`, `service-status.txt`,
`backup-verification.txt`, and `restore-cleanup.txt`.

## Engineering verification and limits

- Complete isolated PostgreSQL suite: **148/148 passed**, zero skips or errors;
  evidence `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T081200Z-write-ahead/`.
- Exact-head GitHub CI: PASS, run [38124162282](https://github.com/ppow1/Riverview-/actions/runs/38124162282)
  at `4276af8`.
- Process graphs: PASS, 13 workflows / 260 nodes; bootstrap persistence,
  transaction, verification, failure and same-token recovery are registered.
- Controlled revision audit: PASS, zero findings.

This commissions the M4.1 PostgreSQL boundary and initial Steward identity. No
application service consumes the token or invokes this registry. Work-order
creation, resident/worker authorization integration, restart recovery through a
service, independent operational observation, and remaining component DoD are
not verified; M4.1 remains **IN PROGRESS**.

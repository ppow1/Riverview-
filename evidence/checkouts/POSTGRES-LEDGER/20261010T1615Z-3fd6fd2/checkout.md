# Riverview~ M1.2 shared development schema migration evidence

**Document Revision:** 1.0.0  
**Task:** RV-M1.2-001  
**Component:** POSTGRES-LEDGER  
**Target:** Camrui development host `admin1-Default-string`, Ubuntu 24.04.3  
**Repository baseline:** merge commit `3fd6fd291d27157697752e7fd02896e514c7388a`; PR #2  
**Date:** 2026-10-10 UTC

## Preflight

- PostgreSQL service active; cluster 16/main, PostgreSQL 16.15, port 5432.
- Connection identity verified without exposing credentials: database `riverview`, role `riverview_core`.
- `riverview_dev` existed, owner `riverview_core`, USAGE and CREATE both true.
- Schema contained no relations before migration. Database size reported 7,727 kB.
- Migration `0001_assignment_event_ledger.sql` was reviewed from source. It creates
  three ledger tables and two indexes only in the selected schema. No migration
  touches `public`, database roles, credentials, or M1.1 service configuration.

## Recoverable backup and restore drill

Full custom-format dump: `/var/backups/riverview/M1.2-20261010T161521Z/riverview-before-m12.dump`  
SHA-256: `e0f3d6126c7f10cc584b4844637904d7a28dc8ad89886f171b372fe25edb4491`  
Permissions: root:root, mode 0600; containing directory root:root, mode 0700.  
Archive structure: `pg_restore --list` succeeded.

Restored into disposable database `rv_m12_restore_20261010_161521` using
`template0`; `pg_restore --exit-on-error` succeeded. PostgreSQL reported the
restored database and two application schemas. The temporary restore copy was
root-controlled then postgres-owned mode 0600 for restore access. The temporary
database and copy were removed; a catalog query confirmed zero such databases.

## Migration and post-deployment checks

Using the project runner against the protected existing passfile and explicit
target `riverview_dev`, result was
`applied_versions: ['0001_assignment_event_ledger']`. Applied checksum:
`7f3580aacc057b977f8dd6f880584d1fed678488523b0d2ce6737c1107487492`.
An immediate second migration run returned `[]`, confirming an idempotent no-op.
The target schema now contains exactly `assignments`, `events`, and
`schema_migrations`. `PostgresLedger` connected and read zero assignments and
zero events. No application rows were written.

After migration, `riverview-baseline.service` was invoked again. systemd result
`success`, exit status 0; a fresh report showed `baseline_ready=true`,
`blocker_code=null`, source commit `64e8f14ad6d71102a864755739a1c8a61506235c`,
target host `admin1-Default-string`, database `riverview`, schema
`riverview_dev`. The M1.1 service unit and release were not changed.

One verification snippet initially attempted `PostgresLedger` as a context
manager, which its API does not provide; that snippet raised `TypeError` after
read-only migration-history/table queries. It was corrected to explicit
`close()` in `finally`, then connection and empty-ledger reads passed. A restore
attempt as the `postgres` OS user could not read the protected root-only backup;
the exact backup was copied temporarily to a postgres-owned mode-0600 location,
restore succeeded, and the temporary copy was removed. Neither issue changed the
target database or backup bytes.

**Outcome:** authorized M1.2 shared development migration and post-deployment
technical checks PASS. This is not full component Definition of Done; dashboard,
always-on processor/autonomy, independent verification, and later roadmap duties
remain open.

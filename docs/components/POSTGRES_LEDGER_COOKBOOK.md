<!--
Riverview~ Controlled Document
File: docs/components/POSTGRES_LEDGER_COOKBOOK.md
Component: POSTGRES-LEDGER
Revision: 1.0.3
Purpose: Diagnose PostgreSQL ledger safely without exposing database credentials
Authority: Read-only diagnostics; migrations and recovery follow reviewed procedures
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-PG-SECRET-SAFETY | Replace password-bearing shell examples with protected authentication guidance
Migration: ENG-REV-002
History: Git and revision backup manifest
-->
# PostgreSQL ledger — operational and troubleshooting cookbook

**Scope:** Camrui developer backend; shared application data is in database `riverview`, schema `riverview_dev`. Never drop `public`, `riverview_dev`, or database `riverview` to fix a test.

## Versioned migrations
Migrations are explicit and target only the selected schema. The ledger
constructor no longer creates tables. For local isolated tests, configure
`RIVERVIEW_TEST_PG_DSN` to a disposable database using a password-free local
socket connection (or the protected test credential facility supplied by the
harness). Do not put passwords in a DSN, command, shell history, process
arguments, or report. Then run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_postgres_ledger.py' -v
```

Each test creates and drops only its uniquely named `rvtest_*` schema. The suite
checks apply/rerun, checksum drift, atomic rollback, state transition rules,
idempotency, event causality, and reconnect persistence. Before any shared-schema
migration, verify host/database/role, schema owner and privileges, current
relations, server compatibility, and the source migration checksum. Capture a
root-protected full database custom-format dump outside the repository, verify its
SHA-256 and `pg_restore --list`, and perform a test restore into a uniquely named
disposable database before applying DDL. Stop on identity, drift, or compatibility
mismatches. Never edit an applied migration to repair it; add a reviewed numbered
forward migration. A checksum mismatch is an integrity failure: preserve the
schema and investigate migration history.

M1.2 migration `0001_assignment_event_ledger` is applied to shared development
schema `riverview_dev`. The 2026-10-10 backup, restore drill, migration checksum,
post-deployment read-only ledger check, and M1.1 service verification are recorded
in `evidence/checkouts/POSTGRES-LEDGER/20261010T1615Z-3fd6fd2/checkout.md`. The
backup remains root-only at the host path recorded there. No live ledger rows
were written during commissioning.

## Known-good baseline
Camrui PostgreSQL 16, database `riverview`, login `riverview_core`, psycopg 3 installed. Six tests passed 2026-10-09; the sixth caught and drove correction of an implicit-transaction persistence bug (commit `166f14a`). This does **not** establish production readiness.

## Inspect service (Camrui)
```bash
systemctl is-active postgresql
pg_lsclusters
ss -lnt | grep 5432
```
Expected: PostgreSQL active, cluster 16/main online, port 5432 listening. These commands do not require the database password.

## Connection and schema inspection

On Camrui, use local PostgreSQL peer authentication for read-only catalog
diagnosis. This reports the PostgreSQL OS peer identity (`postgres`), not the
Riverview runtime identity, and requires no database password:

```bash
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c 'BEGIN READ ONLY; SELECT current_user,current_database(),version(); SELECT nspname,pg_get_userbyid(nspowner) AS schema_owner FROM pg_namespace WHERE nspname IN ($q$riverview_dev$q$,$q$public$q$); SELECT to_regclass($q$riverview_dev.schema_migrations$q$) AS migration_ledger; COMMIT;'
```

Expected database is `riverview`; the application schema is `riverview_dev`.
Only if the migration ledger resolves, inspect its recorded checksums:

```bash
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c 'BEGIN READ ONLY; SELECT version,checksum,applied_at FROM riverview_dev.schema_migrations ORDER BY applied_at,version; COMMIT;'
```

The currently observed schema owner is `riverview_core`; re-read it rather
than assuming ownership has not changed. This administrative peer query does
not prove that the service's runtime credential works. Verify runtime identity
and `LoadCredential` through the relevant unit and its sanitized service checks;
never print, copy, or place `/etc/riverview/pgpass` in a command. If peer auth
or `sudo -n` is unavailable, use the authorized operations path; do not fall
back to inline `PGPASSWORD`, a password-bearing DSN, or relaxing `pg_hba.conf`.

## Run tests safely
```bash
cd /home/admin1/projects/Riverview-New-Core
export PYTHONPATH=src
export RIVERVIEW_TEST_PG_DSN='host=/tmp/<owned-test-socket> port=<test-port> dbname=<disposable-db> user=<test-user>'
python3 -m unittest discover -s tests -v
```
Use only a local isolated cluster whose socket, port, database and user were
created for this test run; the example contains no password. For an external
test server, use a protected passfile or CI secret facility without putting a
password in the DSN or printing it. Expected: all PostgreSQL tests execute (no
DSN-related skip) and report `OK`, exit code 0. Test schemas are uniquely named
and dropped in teardown; if interrupted, list `rvtest_*` schemas, establish
the exact test-run owner, and remove only its exact disposable schema. Never
automate a wildcard `DROP`.

## Symptom -> action
| Symptom | Check | Recovery |
| --- | --- | --- |
| Connection refused | `pg_lsclusters`, `systemctl status postgresql` | Restore cluster service; inspect journal before restarting |
| Password authentication failed | login/database/host; `pg_hba.conf` | Correct credentials/config; do not change DB ownership blindly |
| `No module named psycopg` | `python3 -c 'import psycopg; print(psycopg.__version__)'` | Install `python3-psycopg` on Camrui |
| `No module named riverview_core` | current directory and PYTHONPATH | Run from repository root with `PYTHONPATH=src` |
| Assignment returns to `queued` after reconnect | inspect `autocommit=True` and explicit transactions | Deploy commit `166f14a` or later; rerun persistence test |
| `TransitionError` | `get(id)`, `TRANSITIONS` in `ledger.py` | Supply legal next state; do not bypass verification |
| Idempotency collision | inspect exact idempotency key and prior event | Use new key for genuinely new action; do not delete event |
| Permission denied creating schema | test role schema privileges | Use dedicated authorized test database/role; do not grant blanket superuser |
| Test reports zero PostgreSQL tests | `RIVERVIEW_TEST_PG_DSN` | Set DSN; skipped tests are not proof |
| `schema is not migrated` | Check target schema and `schema_migrations` | Apply only reviewed migrations to the intended disposable or authorized schema |
| Applied migration checksum mismatch | Compare the recorded checksum to the exact SQL file and release commit | Stop; preserve evidence and schema state; correct with a reviewed forward migration |
| Database storage or connection exhaustion | disk, `pg_stat_activity`, logs | Preserve evidence, resolve resource issue; do not delete WAL manually |

## Recovery discipline
1. Capture time, host, service status, error, current commit, and failing test.
2. Stop writes from the affected caller; do not edit event rows to hide a failure.
3. Verify backup and recovery plan before destructive work.
4. Restore service or revert offending code; run six tests in isolated schemas.
5. Reconcile assignment projection against event history, record incident and corrective action.

**Unimplemented:** automatic backups, restore drills, service watchdog, CME escalation, and Steward alerting. See `POSTGRES_LEDGER.md`.

<!--
Riverview~ Controlled Document
File: docs/components/POSTGRES_LEDGER_COOKBOOK.md
Revision: 1.0.2
Migration: ENG-REV-002
-->
# PostgreSQL ledger — operational and troubleshooting cookbook

**Scope:** Camrui developer backend. Never drop the `public` schema or delete the live `riverview` database to fix a test.

## Versioned migrations
Migrations are explicit and target only the selected schema. The ledger
constructor no longer creates tables. For local isolated tests, configure
`RIVERVIEW_TEST_PG_DSN` to a disposable test database and run:

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
```bash
PGPASSWORD='<database password>' psql -h 127.0.0.1 -U riverview_core -d riverview -Atqc 'SELECT current_user,current_database();'
PGPASSWORD='<database password>' psql -h 127.0.0.1 -U riverview_core -d riverview -c '\dt'
```
The first result should be `riverview_core|riverview`. The second lists tables if they have been initialized in `public`. For normal tests, only temporary `rvtest_...` schemas are created and removed.

## Run tests safely
```bash
cd /home/admin1/riverview-core
export PYTHONPATH=src
export RIVERVIEW_TEST_PG_DSN='postgresql://riverview_core:<database password>@127.0.0.1:5432/riverview'
python3 -m unittest discover -s tests -v
```
Expected: all PostgreSQL tests execute (no DSN-related skip) and report `OK`, exit code 0. Test schemas are uniquely named and dropped in teardown; if interrupted, inspect `SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'rvtest_%';` before removing any orphaned schema. Never automate a wildcard DROP.

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

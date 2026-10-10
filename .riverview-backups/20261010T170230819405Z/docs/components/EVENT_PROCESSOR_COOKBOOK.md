# Riverview~ event processor cookbook

**Document Revision:** 1.0.1
**Component:** EVENT-PROCESSOR  
**Task:** RV-M1.3-001  
**Status:** IN PROGRESS; controlled Camrui commissioning  
**Authority:** Development schema `riverview_dev`; M1.1 runtime configuration is independent.

## Isolated schema setup and migration

Set `RIVERVIEW_TEST_PG_DSN` to a disposable PostgreSQL test database. The test
suite creates and drops only unique `rvtest_*` schemas. It first applies the
POSTGRES-LEDGER base migrations, then explicitly applies the processor cursor
migration from its separate directory. Do not point this suite at the live
`riverview_dev` schema.

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='host=/tmp/rv-pgtest/socket port=55432 dbname=postgres user=postgres' python3 -m unittest tests.test_event_processor -v
```

## Operational signals and recovery

- `processor_started`: consumer, schema, cursor, and database leadership acquired.
- `event_processed`: source event sequence and result (`advanced`,
  `already_advanced`, or `ignored`); payload is not logged.
- `processor_retry`: failure class and bounded retry delay; cursor remains before
  the unhandled event.
- `processor_stopped`: final durable cursor after signal-driven stop.
- `another processor holds this consumer lease`: inspect systemd process state;
  do not start a second instance with the same processor ID.

After restart, confirm the journal shows `processor_started` and cursor position,
then verify the assignment and event history in the selected development schema.
If retries persist, record the earliest uncheckpointed sequence and failure
class, preserve PostgreSQL logs, and diagnose the dependency before changing or
skipping any cursor. Never advance the cursor manually to hide a poison event.

## Camrui commissioning and recovery

The M1.3 service is isolated from `riverview-baseline.service` and uses the
root-owned deployment link `/opt/riverview-event-processor` to a commit-named,
root-owned release under `/opt/riverview/releases/`. Its unit is
`riverview-event-processor.service`; it uses the existing
`/etc/riverview/pgpass` through systemd `LoadCredential`, then creates a private
mode-0600 passfile under `/run/riverview-event-processor/`. Do not place passwords
in a DSN, environment file, command argument, journal, or evidence artifact.

Before applying M1.3 migration 0002:

1. Run the M1.1 baseline check and inspect PostgreSQL/service status.
2. Confirm `riverview_dev` is owned by `riverview_core`, migration 0001 has the
   expected source checksum, and 0002/cursor table are absent.
3. Capture a root-only custom-format backup of database `riverview`; verify its
   SHA-256 and `pg_restore --list` output.
4. Restore the backup to a uniquely named disposable database and verify the
   M1.2 tables and migration record; drop only that disposable database.
5. Stage the verified package with `deploy/install_event_processor.sh`. The
   script preserves the prior service/link, does not alter M1.1, and leaves M1.3
   stopped until migration and preflight succeed.
6. Apply only the reviewed cursor migration through
   `src/riverview_core/postgres_migrations.py` with schema `riverview_dev` and
   the separate M1.3 migrations directory. Check the exact recorded checksum and
   cursor table before enabling the service.
7. Enable/start only `riverview-event-processor.service`. Verify fresh status,
   journal events, cursor row and a unique acceptance assignment with
   `scripts/verify_event_processor.py`.
8. Restart the M1.3 unit and create a second unique acceptance assignment;
   verify it advances and that the same consumer cursor continues monotonically.

The installer prints the root-only rollback directory. Recovery is
`sudo /opt/riverview-event-processor/deploy/rollback_event_processor.sh <recorded-directory>`.
It restores the prior M1.3 unit/link and enabled/running state; it deliberately
retains migration 0002, cursor history and the pre-deployment database backup.
Do not drop the cursor table during code rollback.

To verify database-session recovery, identify the single granted advisory lock
held by application name `riverview-event-processor`, terminate only that exact
backend, and confirm the journal records `processor_dependency_retry` followed
by a new `processor_started`. Verify there is again exactly one granted consumer
lock and the service remains active. Never terminate unrelated database
backends. M1.1 and PostgreSQL are not restarted for this fault injection.

## Current status

M1.3 technical commissioning status and time-bounded unattended observations are
maintained in revisioned acceptance and evidence records. Full component DoD
items such as the live dashboard and later autonomy integrations remain
outstanding independently.

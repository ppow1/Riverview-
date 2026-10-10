# Riverview~ event processor cookbook

**Document Revision:** 1.0.0  
**Component:** EVENT-PROCESSOR  
**Task:** RV-M1.3-001  
**Status:** IN PROGRESS; no installed service  
**Authority:** Development/test database only until deployment acceptance.

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

## Current status

Unit installation, systemd restart, shared-schema processor migration, long-run
monitoring, remote observability and production recovery are not yet verified.
Do not claim M1.3 completion based on the isolated test suite.

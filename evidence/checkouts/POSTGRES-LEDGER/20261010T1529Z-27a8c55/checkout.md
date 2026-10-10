# Riverview~ RV-M1.2-001 committed-source checkout

**Document Revision:** 1.0.0
**Task:** RV-M1.2-001
**Component:** POSTGRES-LEDGER
**Timestamp UTC:** 2026-10-10T15:29Z
**Source commit:** `27a8c555501588dd0fd2a5d488018ad0c295199a`
**Branch:** `codex/m1.1-runtime-commissioning`
**Host:** `admin1-Default-string`; Ubuntu 24.04.3; user `admin1`
**Test database:** disposable PostgreSQL 16 UTF-8 cluster on private Unix socket
**Outcome:** PASS for M1.2 isolated technical acceptance cases; no milestone acceptance claimed

## Execution

The cluster was created under a unique `/tmp/rv-m12-pgtest.*` path with
`initdb -U postgres -A trust --no-locale --encoding=UTF8`, bound to a private
Unix socket and temporary port 55439. No network listener was opened. It was
stopped and removed after verification.

Exact test invocation:

```text
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN="host=$TEST_SOCKET port=55439 dbname=postgres user=postgres" python3 -m unittest discover -s tests -v
```

**Result:** 53 tests run, 53 passed, 0 failed, 0 skipped. Six PostgreSQL tests
executed, including migration application/rerun/checksum drift and missing-schema
rejection; atomic transition rollback on injected event failure; transition and
idempotency rules; two-assignment independence; event causality; and reconnect
persistence. Fifteen revision-control tests also passed.

`initdb.log`, `start.log`, `unittest.log`, `stop.log`, and the failed-attempt
record are included and checksummed by `artifacts.json`. The revision baseline
checkout was separately clean with zero issues before commit. The commissioned
M1.1 database/schema, credentials, and `riverview-baseline.service` were not
changed. The broader component DoD, M1.1 Steward acceptance, shared-schema M1.2
deployment, and M1.2 acceptance remain open.

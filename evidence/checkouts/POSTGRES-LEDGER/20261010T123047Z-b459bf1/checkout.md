# RV-M1.1-006 PostgreSQL integration checkout

**Document Revision:** 1.0.0
**Task / component:** RV-M1.1-006 / POSTGRES-LEDGER
**Timestamp UTC:** 2026-10-10T12:30:47Z
**Source commit:** `b459bf1691b9d92811185b0a5b7013a28ac40752`
**Host:** `admin1-Default-string`, Ubuntu 24.04.3, PostgreSQL 16.15
**Actor:** Codex on Camrui

## Scope and setup

Executed the three PostgreSQL integration tests skipped in the prior run, using a disposable PostgreSQL 16 cluster in `/tmp/rv-pgtest.uEU8h2I0`. The cluster listened only on its private Unix socket; trust authentication was confined to this isolated test cluster. The installed `16/main` cluster was not used or modified. Setup, startup, server and shutdown logs are attached.

Exact test command:

```sh
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN="host=/tmp/rv-pgtest.uEU8h2I0/socket port=5432 dbname=postgres user=admin1" python3 -m unittest discover -s tests -v
```

## Results

Exit code 0. 36 tests passed, 0 failed, 0 skipped. The PostgreSQL cases that executed were:

- `test_completion_requires_verification_flag`
- `test_idempotency_and_illegal_transition`
- `test_persistence_and_independent_assignments`

The tests create isolated `rvtest_<uuid>` schemas and remove them in teardown. After test execution, the disposable server was restarted and queried with:

```sql
SELECT current_setting('server_version') || '|' || current_setting('listen_addresses') || '|' || count(*)
FROM pg_namespace WHERE nspname LIKE 'rvtest_%';
```

Observed output: `16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)||0`; empty listen-address value denotes no TCP listener, and zero matching schemas confirms cleanup. The disposable cluster was then stopped successfully. No secrets are included in evidence.

## Limits and decision

This verifies the integration tests against isolated local PostgreSQL only. It does not prove installed-cluster password authentication, runtime service installation, systemd operation, rollback, external observation, or Steward acceptance. M1.1 is not DONE. The local privileged installer/acceptance step requires sudo authorization; runtime DB authentication requires the existing `riverview_core` credential to be securely provisioned. Steward acceptance is pending. Do not advance to M1.2.

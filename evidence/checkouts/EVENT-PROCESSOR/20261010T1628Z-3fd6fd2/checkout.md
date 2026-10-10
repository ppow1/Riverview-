# Riverview~ M1.3 isolated event processor verification

**Document Revision:** 1.0.1  
**Task:** RV-M1.3-001  
**Component:** EVENT-PROCESSOR  
**Parent:** M1.2 technical merge `3fd6fd291d27157697752e7fd02896e514c7388a`  
**Host:** `admin1-Default-string`, Ubuntu 24.04.3  
**Timestamp:** 2026-10-10 UTC

## Executed verification

The latest complete repository suite passed **67 tests, 0 failures, 0 errors,
0 skips** with a fresh disposable PostgreSQL 16.15 cluster. PostgreSQL accepted
connections only over its local Unix socket, with local trust and rejected host
authentication. The private data directory remained postgres-owned; only the
socket path was traversable to `admin1`. All unique `rvtest_*` schemas were
removed (catalog count 0), the cluster was stopped and deleted.

The suite includes all six M1.2 PostgreSQL integration tests and four M1.3
processor integrations: unattended progression and process restart, crash-window
replay without duplicate transition, repeated consumer idempotency, and handler
failure without cursor advancement followed by retry. Ten graph tests cover schema
conformance, global IDs, references, edge types, dependency/runtime separation,
jumps, extensions, sidecar checksums, generated synchronization, and compact
aggregate view behavior.

Full output and exact command are in `test_results.json`. The M1.3 processor loop
was exercised in test threads; no M1.3 systemd unit, secure systemd credential
handoff, shared M1.3 migration or unattended service deployment has been
performed. M1.3 remains IN PROGRESS, not accepted. M1.1 service and shared M1.2
schema were not used by this test run.

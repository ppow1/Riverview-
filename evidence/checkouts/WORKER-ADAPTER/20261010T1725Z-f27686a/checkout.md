# Riverview~ M2.1 isolated worker-adapter verification

**Document Revision:** 1.0.0
**Task:** RV-M2.1-001
**Component:** WORKER-ADAPTER
**Milestone:** M2.1 — minimal registered worker adapter
**Environment:** Camrui, Ubuntu 24.04.3, PostgreSQL 16.15 disposable UTF-8 cluster
**Source commit:** `f27686ad7087ce9ea828c21ec584d45ef3bb5f84`
**Status:** Isolated implementation verified; operational deployment and full DoD open

## Implementation and verification

A registered worker receives a high-entropy credential once; PostgreSQL stores
only its SHA-256 digest. Execution requires a valid credential, registered
capability, exact worker scope/assignment authority match, and current M1.4 lease
generation. The only executable capability is deterministic local SHA-256 over
explicit UTF-8 input. The adapter persists attributed attempts and result
records, rejects idempotency-key reuse with different input, and rechecks the
lease before committing results. The input itself is not stored.

The exact source tree passed **80 tests, zero failures, zero errors, zero skips**.
Three M2.1 PostgreSQL tests verified scoped authenticated execution, capability
and credential/scope rejection, durable result/replay and key-collision behavior,
and visibility of a durable unfinished attempt. The unfinished-attempt test
simulated an interrupted attempt by retaining a `running` database record; it did
not kill a worker process or demonstrate autonomous process restart/recovery.

All unique `rvtest_*` schemas were removed (final count zero) and the isolated
PostgreSQL cluster was stopped. The suite output is `unittest.log`.

Canonical graph validation passed with seven workflows and 105 nodes. The
revision audit passed against the established repository baseline. No M2.1 DDL
was applied to shared `riverview_dev`; no M2.1 service was deployed. The live
M1.1/M1.2/M1.3 state was not modified.

The full component DoD remains open, including supervised worker lifecycle,
operational failure/recovery verification, live visualization and external
observability. M2.1 isolated CI/PR checks are tracked by PR #8.

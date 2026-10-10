# Riverview~ M1.3 isolated event processor verification

**Document Revision:** 1.0.0  
**Task:** RV-M1.3-001  
**Component:** EVENT-PROCESSOR  
**Parent:** M1.2 technical merge `3fd6fd291d27157697752e7fd02896e514c7388a`  
**Host:** `admin1-Default-string`, Ubuntu 24.04.3  
**Timestamp:** 2026-10-10 UTC

## Executed verification

Ran the complete repository suite with a disposable PostgreSQL 16.15 cluster,
Unix socket only, local trust authentication and host authentication rejected.
The cluster data directory remained postgres-owned/private; the socket path was
made traversable solely to allow `admin1` test connections. The test suite used
unique `rvtest_*` schemas, removed them all, and the temporary cluster was shut
down and deleted.

**Result:** 66 tests, 0 failures, 0 errors, 0 skips. The suite includes four M1.3
PostgreSQL integration tests: unattended assignment progression and restart,
crash-window replay without duplicate transition, repeated same-consumer
processing, and failure without cursor advancement followed by retry. Six M1.2
PostgreSQL tests also ran. Graph validation covers schema, global uniqueness,
edge/jump references, extension types, sidecar checksums and synchronized views.

Full test names and captured output are in `test_results.json`. The test
processor was a thread exercising its continuous loop, not an installed systemd
service. M1.3 remains IN PROGRESS: its Linux unit, secure systemd credential
delivery, actual supervised deployment, independent operational observation and
roadmap acceptance are not yet verified. M1.1 live service and shared M1.2 schema
were not used by this test run.

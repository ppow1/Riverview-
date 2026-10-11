<!--
Riverview~ Controlled Evidence Record
File Revision: 1.0.0
Component: RESIDENT-ORCHESTRATION
Task: RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE
-->
# Committed-source integration checkout

**Source commit:** 8c463af92b31a10afe53af2426ad99a3310613e0.
**Result:** 205 tests passed; zero failures, errors, or skips; 62.280 seconds.
**Environment:** Disposable PostgreSQL 16.15 private socket cluster and per-test random schemas. The DSN value is intentionally omitted. The integration test drops its isolated schema after each test.
**Command:** `PYTHONPATH=src python3 -m unittest discover -s tests -v`, with private `RIVERVIEW_TEST_PG_DSN` and the evidence directory set for the test process.
**End-to-end result:** objective:grace-e2e reached COMPLETED after exact-grant objective intake, verified commit-pinned evidence, unapproved typed proposal, exact-grant assignment creation, scheduler lease, worker attempt, actual work-product file, and independently accepted persisted verification. See integration-result.json and the nested artifact manifest.
**Limit:** Deterministic reasoning fixture and local artifact worker only. This does not establish a live Grace resident, production deployment, commissioned coding service, dashboard interaction, or full M4.4 acceptance.

**Process graph:** `process_graph.py check` PASS; `process_graph.py validate` PASS; 16 workflows / 323 nodes.
**Controlled revisions:** revision audit PASS with zero findings against a clean checkout of source commit 8c463af92b31a10afe53af2426ad99a3310613e0.

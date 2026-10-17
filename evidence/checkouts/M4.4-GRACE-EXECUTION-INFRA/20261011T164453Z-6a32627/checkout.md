<!--
Riverview~ Controlled Evidence Record
File Revision: 1.0.0
Component: RESIDENT-ORCHESTRATION
Task: RV-M4.4-OBJECTIVE-WORKORDER-PIPELINE
-->
# Pre-commit integration run

**Evidence class:** Development working-tree test run; not exact-commit acceptance evidence.
**Parent commit:** 6a326279aa4e81211b8a4fdc998d1e94c2361370.
**Result:** 205 tests passed, zero failures/errors/skips, using an isolated temporary PostgreSQL 16.15 cluster.
**Command:** `PYTHONPATH=src python3 -m unittest discover -s tests -v` with private `RIVERVIEW_TEST_PG_DSN` and evidence-capture directory set in the process environment. The DSN value is intentionally omitted.
**Scope:** Complete suite; actual objective/work-order E2E record and file artifact are in `integration-result.json` and `artifacts/bounded-work-product.json`.
**Limit:** This was run before the source commit. Use the separate committed-source checkout record for final acceptance evidence.

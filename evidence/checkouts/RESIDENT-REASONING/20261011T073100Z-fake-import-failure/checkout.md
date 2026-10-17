<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/RESIDENT-REASONING/20261011T073100Z-fake-import-failure/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Retain PostgreSQL-backed test failure for fake provider import diagnosis
Authority: Private PostgreSQL test cluster only
Changed: 2026-10-11 UTC | RV-M4.2-FAKE-PROVIDER-IMPORT-FIX | Preserve NameError test outcome and exact fixture cleanup
History: artifacts.json SHA-256 manifest
-->
# Fake knowledge-provider test failure

Focused command: `RIVERVIEW_TEST_PG_DSN=<private PostgreSQL 16.15 socket DSN> PYTHONPATH=src python3 -m unittest tests.test_resident_reasoning -v`. Result: 1 passed and 4 failed. Root cause: test fixture `_Knowledge._result` referenced `KnowledgeStatus` without importing it in that method, causing a fixture `NameError`; production code correctly failed closed. Read-only private-cluster teardown queries returned zero `rvtest_*` schemas and zero `rvtest_*` roles. The isolated server remains available only to rerun the corrected test and will be stopped afterward. No Camrui shared state changed.

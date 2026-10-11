<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/RESIDENT-REASONING/20261011T073000Z-initial-failure/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Retain initial PostgreSQL-backed M4.2 failure and cleanup evidence
Authority: Disposable private PostgreSQL only; no Camrui shared state
Changed: 2026-10-11 UTC | RV-M4.2-001 | Preserve failed test run and diagnosis
History: artifacts.json checksums
-->
# Initial M4.2 integration failure

The first five-test run reported 4 passed and 1 failed. The `plan_and_grounding_are_durable_across_runtime_replacement` test exhausted its scripted fake knowledge status list when a replacement runtime grounded again. The resident runtime correctly treated the resulting provider exception as unavailable and waited; the defect was in the fake fixture, which was then changed to default to reusable VERIFIED results when its explicit test sequence is empty.

The disposable cluster remained up because the shell exited on the failed test. Read-only cleanup queries returned zero `rvtest_*` schemas and zero `rvtest_*` roles; only the private cluster was stopped. Its socket subsequently returned no response. No shared database/service state was changed.

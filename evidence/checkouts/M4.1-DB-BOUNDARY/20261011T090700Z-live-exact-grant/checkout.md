# RV-M4.1 Live exact-grant migration and ACL commissioning

**Document Revision:** 1.0.0
**Component:** INSTITUTIONAL-AUTHORITY
**Task:** RV-M4.1-GRANT-ENFORCEMENT-COMMISSIONING
**Source commit:** 36622e573f9e030aba909967be76fc4cd646b620
**Environment:** Camrui, Ubuntu 24.04.3, PostgreSQL 16.15; isolated restore DB for recovery rehearsal; shared Riverview development DB received additive authority migration and narrow reviewed ACL change.
**Result:** Migration 0002 applied once, migration runner idempotency returned no pending migrations, boundary apply succeeded and subsequent preflight was clean. Runtime role got exact function EXECUTE only; direct table reads denied. A transaction-only live role check proved allow/deny and rolled back every synthetic row. Protected backup restore rehearsal passed and its disposable database was removed. Existing service units remained active.
**Limit:** This deploys the database function/ACL only. The worker adapter is not deployed into a worker service; assignment.create is not yet guarded; no real worker assignment or M3.3 end-to-end acceptance is claimed. PR #21 remains open/draft/unmerged.

# RV-M4.1 Exact-grant and worker integration evidence

**Document Revision:** 1.0.0
**Component:** INSTITUTIONAL-AUTHORITY / WORKER-ADAPTER
**Task:** RV-M4.1-GRANT-ENFORCEMENT
**Base source commit:** c9ab1e6048146006d13770f375fccfd2b33bc8f2
**Environment:** Ubuntu 24.04.3; Python; isolated PostgreSQL 16.15 socket-only disposable cluster; no live database writes
**Result:** Full suite 150/150 pass, zero skips/errors/failures; focused boundary/worker/CME 22/22; migration regression 1/1; graph 13 workflows/265 nodes PASS; revision audit no issues; compileall exit 0.
**Limit:** Source-level and isolated integration evidence only. Live migration 0002 and function-only ACL deployment are not applied; no live worker or assignment test. Camrui authority state was read-only preflighted and preserved.

# M4.1 database boundary and dashboard documentation checkpoint

- Task: `RV-M4.1-DB-BOUNDARY`
- Source commit: `167e63b9969a5cdbb1e4d3abee33e3e503bba11f`
- Branch: `codex/m4.1-db-privilege-boundary`
- PR: #20 (open, draft, unmerged; base PR #18 branch)
- Target: Camrui Ubuntu 24.04; disposable PostgreSQL 16.15, Unix socket only, port 55482.
- Shared database: read-only diagnostics only; no object, role, credential, migration, assignment, worker, service or configuration was changed.

## Verification

- Full isolated suite: **133 passed, 0 failures, 0 errors, 0 skips**.
- Updated dashboard authority-cookbook HTTP route: **1/1 passed**; rendered HTML includes safe headings, tables/code, expected boundary warnings, no metadata comments.
- Python compileall: exit 0.
- Process graph: **PASS**, 12 workflows / 226 nodes.
- Controlled revision/predecessor audit: **PASS**, zero findings.
- PostgreSQL test fixture cleanup: zero `rvtest_*` schemas and roles; private cluster stopped successfully.
- Exact-head GitHub CI: **PASS**, run 38115448463.
- Camrui live services: Postgres, event processor, CME monitor, notification dispatcher and dashboard active; baseline oneshot `Result=success`. Dashboard returns HTTP 200 at the existing release. Read-only counts: 9 migrations; 4 assignments (1 completed/3 ready); 11 events; 1 attempt; 1 verification; 6 monitor events; 3 notices.

## Deployment decision

Package manifest, shell bytes and archive paths were verified. Deployment was deliberately withheld because the candidate would replace the active dashboard shell revision 1.0.6 with branch revision 1.0.5 and remove repository-knowledge documentation links. Existing release `7a9ff46e11edc54b1ffe46f63962754e6d2da765` remains selected. No live authority schema or service has been commissioned.

**Isolated M4.1 engineering: PASS. M4.1 live commissioning and full DoD: OPEN.** Shared schema `riverview_dev` is runtime-owned and must fail the role-boundary preflight. Protected authority-manager credential/service integration, distinct schema/migration owner, backup/restore rehearsal and assignment/worker authorization remain unverified.

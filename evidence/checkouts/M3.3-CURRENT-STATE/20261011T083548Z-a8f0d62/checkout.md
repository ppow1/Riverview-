<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/M3.3-CURRENT-STATE/20261011T083548Z-a8f0d62/checkout.md
Component: CME-FIRST-VERTICAL-SLICE
File Revision: 1.0.0
Purpose: Verify current M3.3 authority blocker, full isolated regression, graph, and revision records
Authority: No live assignment without application-enforced grant and verified knowledge
Source: codex/m3.3-repository-knowledge at a8f0d6276b45bf51f523825527f5f9e3c80cd250
History: artifacts.json SHA-256 manifest
-->
# M3.3 current-state and regression checkpoint

## Scope and status

This checkpoint reconciles the M3.3 blocker with later scoped M4.1 live database-boundary/bootstrap evidence. It does not perform live M3.3 work or claim M3.3/M4.1 acceptance. The authority registry exists and has scoped grants, but application assignment/worker paths do not enforce them. The repository knowledge provider remains unconfigured in the live worker; no general institutional provider is available. No shared assignments, worker registrations, credentials, schemas, or services were changed in this task.

## Verification

- Canonical CI command: `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN=postgresql://admin1@/postgres?host=/tmp/riverview-test-pg-overnight/socket&port=55439 python3 -m unittest discover -s tests -v`
- Result: **143 tests passed, zero failures/errors/skips** against a disposable PostgreSQL 16.15 cluster, run as `admin1` so the repository provider's pinned-Git checks operate normally.
- Graph validation: **PASS**, 13 workflows / 235 nodes.
- Controlled revision audit: **PASS**, zero findings.
- `git diff --check`: PASS.
- Cleanup: temporary system-cluster database `riverview_test` had zero `rvtest_*` schemas, roles, and active connections, then was dropped. The socket-only cluster was stopped and its generated directory removed. Evidence reports both schema and role counts as zero; cleanup verification passed.

The initial attempt to run under OS user `postgres` produced two pinned-provider test errors because that user could not read the worktree's Git metadata. The corrected run as `admin1` against the disposable cluster passed. A broad `pytest` probe was not the repository command and attempted to collect archived historical tests outside `tests/`; the prescribed CI `unittest` command passed.

## Artifacts

`full-suite.log`, `process-graph-check.json`, `revision-audit.json`, `diff-check.txt`, `test-schema-cleanup.txt`, `live-service-status.txt`, and `test-infrastructure-cleanup.txt` are hashed in `artifacts.json`. Six Camrui service units (PostgreSQL, event processor, CME monitor, notification dispatcher, dashboard, SSH) returned `active` at collection. The live status is observational; this checkpoint did not deploy or restart a service.

M3.3 remains **BLOCKED** pending application-level grant enforcement and live worker/provider commissioning. Historical observations remain preserved and identified as pre-M4.1 state. Exact current corrections are in `docs/ROADMAP.md` revision 1.1.16, `docs/development/M3.3-001_REVISION_RECORD.md` revision 1.0.8, and `docs/development/JOURNAL.md` revision 1.0.72.

<!--
Riverview~ Controlled Checkout Evidence
File Revision: 1.0.2
Component: RESIDENT-ORCHESTRATION / INSTITUTIONAL-PROPOSALS
Task: RV-C3-GRACE-ENGINEERING-E2E-001; RV-C3-CANDIDATE-INTEGRATION-GAP-001
-->
# C3 lifecycle checkout evidence

**Result:** PASS for candidate synthetic lifecycle tests and final repository graph/revision checks; component DoD remains NOT DONE.  
**Timestamp:** 2026-10-18 18:05 UTC (2026-10-18 14:05 EDT), after the final full-suite run.  
**Host:** Camrui, Linux; Python 3.12.3; Git worktree `/home/admin1/projects/Riverview-Grace-Engineering-E2E`.  
**Branch:** `codex/grace-engineering-e2e-preparation-20261018`.  
**Source commit tested:** `3a2e9b9fdec0b5c5a7ed6264147af300f93ca6cf`.  
**Database:** Disposable PostgreSQL 16 `regress` cluster managed by Debian `pg_virtualenv`, created for each test invocation and dropped on exit. The host's `16/main` cluster was not used. DSN is omitted; no credentials are recorded.

## Commands and outcomes

| Check | Command | Exit | Result |
|---|---|---:|---|
| Focused lifecycle | `pg_virtualenv bash -c 'cd /home/admin1/projects/Riverview-Grace-Engineering-E2E && RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" PYTHONPATH=src python3 -m unittest discover -s tests -p test_proposal_work_order_lifecycle.py -v'` | 0 | 11 tests passed; no skips; 42.719 s |
| Full suite | `pg_virtualenv bash -c 'cd /home/admin1/projects/Riverview-Grace-Engineering-E2E && RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" PYTHONPATH=src python3 -m unittest discover -s tests -v'` | 0 | 626 tests; 1 skip; 0 failures/errors; 598.830 s |
| Graph schema/links | `python3 scripts/process_graph.py validate` | 0 | 22 graphs PASS |
| Graph and generated views | `python3 scripts/process_graph.py check` | 0 | 22 graphs / 565 nodes PASS |
| Controlled revision audit | `python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json` | 0 | PASS; no findings; see `logs/revision-control-final.log` |
| Saved predecessor/restore verification | `python3 evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/verify_predecessors.py` | 0 | 2/2 predecessors exact; 2/2 temporary restores PASS |

The sole full-suite skip was `test_restricted_riverview_core_role_can_read_only_grace_health_after_migration`: the disposable cluster does not define the dashboard runtime role. It is preserved as a skip, not treated as exercised. Historical exact-head GitHub controlled checkout run 39143415162 also passed (626 tests, 4 skips); its result is supplementary and separate from this local run.

## Scope and limitations

The new lifecycle tests use synthetic approvals, test identities/grants, fixture reasoning and disposable PostgreSQL. The apparent `synthetic-80b` provider is only a fixture. The bounded artifact worker and independent verifier test the code path but do not establish a commissioned production worker, real Steward interaction, live 80B result, authenticated production conversation, deployed operational view, or repeated unattended live cycles. No production database, service, credential, grant, external model or live objective was touched.

The initial revision audit failure is retained in `logs/revision-control.log`; it exposed a missing sidecar for the nested logs directory and did not reflect a source/test failure. The final successful rerun is in `logs/revision-control-final.log`; see the lifecycle supplement for the correction and predecessor record. Logs (including exact unittest summaries and graph/revision JSON) are in `logs/`. `predecessor-restoration.log` contains hashes, source commit/blob IDs and successful temporary restore outcomes. `artifacts.json` records sizes, revisions and SHA-256 for evidence files.

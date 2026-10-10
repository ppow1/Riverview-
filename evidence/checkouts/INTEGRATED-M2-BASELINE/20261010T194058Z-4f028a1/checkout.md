# Integrated M2.1–M2.3 baseline checkout

**Document Revision:** 1.0.1  
**Task:** RV-M2-BASELINE-001  
**Source repository:** `ppow1/Riverview-`  
**Source commit:** `4f028a138c41665239bde2c11be65b0f841f02bf`  
**Host:** Camrui, Ubuntu 24.04.3  
**Run time:** 2026-10-10 19:40 UTC  
**Classification:** Isolated integration verification; not live operational commissioning.

## Repository and integration verification

The main repository checkout was clean before testing. `origin/main` resolved to the exact expected commit. The merge history contains PR #9 at `b0a5b818b188a97a800988b7781d59578c318954`, PR #10 at `b4b8339c492b2cf0d7e230b27575c2cebcea33fc`, and PR #12 at `4f028a138c41665239bde2c11be65b0f841f02bf`. The requested clean integration worktree was detached at `origin/main`; the original M2.3 worktree was preserved until it was cleanly fast-forwarded to `main`.

## Test and audit results

- Full integrated suite: `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='host=<private socket> port=55439 dbname=postgres user=admin1' python3 -m unittest discover -s tests -v` — **89 passed, 0 failed, 0 errors, 0 skipped**.
- PostgreSQL: private PostgreSQL 16.15 Unix-socket-only cluster; test fixtures used disposable `rvtest_*` schemas; post-run residual schema count **0**; cluster stopped.
- Process graph: `python3 scripts/process_graph.py check` — **PASS**, 10 workflows, 156 nodes.
- Controlled revisions: repository CI baseline audit — **PASS**, zero issues.
- GitHub CI on integrated main: [run 38079898010](https://github.com/ppow1/Riverview-/actions/runs/38079898010) — success for the exact source commit.
- Knowledge provider package: contract version **1.0.0** is intact at `src/riverview_core/worker_adapter/knowledge_provider_v1/`; its immutable source commit is recorded in the manifest.
- Grace: mandatory M4.4 requirements remain in the roadmap, Core Contract, process graph, and Component DoD. They remain future implementation/acceptance obligations.

## Branch reconciliation

Git ancestry verified each source branch is contained in `origin/main`; `git rev-list --left-right --count origin/main...origin/<branch>` returned zero branch-only commits for all three. PR #9, #10, and #12 were merged to `main`. Only those three M2.1–M2.3 feature branches were deleted, remotely and locally, with ordinary non-force deletion. The archive branch and remaining historical commissioning branches were not deleted. `main` is the authoritative baseline at the source commit above.

The isolated suite does not demonstrate deployed M2.1–M2.3 services, shared-schema commissioning, live dashboard operation, Grace autonomy, or full component DoD acceptance.

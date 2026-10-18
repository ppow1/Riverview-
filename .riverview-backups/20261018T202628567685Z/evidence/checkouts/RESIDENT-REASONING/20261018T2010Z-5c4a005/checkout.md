<!--
Riverview Controlled Evidence
File: evidence/checkouts/RESIDENT-REASONING/20261018T2010Z-5c4a005/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.2
Purpose: Record C3 exact proposal review implementation and isolated verification
Execution Model: Disposable PostgreSQL 16 integration tests and mocked local provider tests
Observability: Test logs, revision audit, source commit, predecessor backup hashes
Dependencies: Python 3.12.3; PostgreSQL 16.15; repository unittest suite
Authority: Synthetic provider fixtures only; no production service, credentials, grants, browser or live ChatGPT
Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Capture exact-commit isolated acceptance evidence
Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Append receipt/owner-cycle implementation and exact offline test evidence
Changed: 2026-10-18 UTC | RV-C3-CHATGPT-EXACT-REVIEW-001 | Record C2 exception-code compatibility and final 38-test rerun
Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md; docs/components/RESIDENT_REASONING.md
Tests: tests/test_external_reasoning_exchange.py; tests/test_resident_reasoning.py; tests/test_local_reasoning_provider.py
History: Git and .riverview-backups/manifest.jsonl
-->
# C3 exact proposal review and doorbell exchange checkout evidence

- **Task:** `RV-C3-EXACT-PROPOSAL-REVIEW-001`
- **Host/environment:** Camrui Ubuntu 24.04; isolated worktree `/home/admin1/projects/Riverview-Grace-Review-C3`
- **Branch:** `codex/c3-exact-proposal-review-20261018`
- **Source base commit:** `5c4a00512e5acd6f72aa766ea866a8828184b151`; follow-up commit is recorded in the PR and GitHub issue.
- **Base:** PR #119 head `97128626df967bc992696dca38eaa7116f3616e9`
- **PR:** https://github.com/ppow1/Riverview-/pull/135 (draft at evidence creation)
- **Run began (UTC): `2026-10-18T20:09:43Z`; final commands completed before this evidence commit.
- **Runtime versions:** Python 3.12.3; PostgreSQL 16.15; `pg_virtualenv` 16/regress temporary cluster.

## Commands and outcomes

1. Initial run of the receipt/resident command exited 1 because the deterministic attempt UUID helper was not imported. The code was corrected and the failure is preserved in `attempts/failed-debug-attempts.md`.
2. `pg_virtualenv -t sh -c 'export RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER password=$PGPASSWORD"; PYTHONPATH=src python3 -m unittest tests.test_external_reasoning_exchange tests.test_resident_reasoning -v'` — exit 0; **37 passed, 0 failed** on disposable PostgreSQL 16.15. The temporary cluster was destroyed. Coverage includes exact subject digest/tamper, digest echo, Grace finish/revise/restart recovery, body-free doorbell claim, receipt idempotency and token binding, bounded pre-send retry, terminal ambiguous result, authority, expiry, and resident regressions.
3. After the first full run, C2 exception-code compatibility was added and four receipt cases were rerun — **4 passed, 0 failed** on a disposable PostgreSQL 16 cluster.
4. Final full command was rerun after that correction; exit 0; **38 passed, 0 failed**, in 60.144 seconds, completed at **2026-10-18 20:24:38 UTC**. Full raw output is `final-exchange-and-resident-postgres.log`.
5. `PYTHONPATH=src python3 -m unittest tests.test_local_reasoning_provider -v` — exit 0; **31 passed, 0 failed**. Includes local prompt binding of subject and advisory as separate inputs.
6. `python3 -m compileall -q src/riverview_core/resident_execution/external_reasoning.py src/riverview_core/resident_execution/service.py tests/test_external_reasoning_exchange.py` — exit 0.
7. `git diff --check` — exit 0.
8. `python3 scripts/revision_control.py check --baseline evidence/checkouts/RESIDENT-REASONING/20261018T2010Z-5c4a005/pre-edit-revision-baseline.json` — **PASS, zero findings**.
9. Initial review commit predecessor restore check — **10/10 PASS**. Follow-up snapshots — **17/17 PASS**; files readable and SHA-256 matches manifest (`followup-predecessor-verification.log`).
10. Exact-head controlled-checkout CI for initial PR head — run **39161980119 SUCCESS**. New exact-head CI is required for the follow-up commit.


Expected synthetic crash-injection tests emit only sanitized `failure_type: RuntimeError` event lines while asserting recovery; no prompt/advisory bodies or credentials are logged. All observed failed debugging attempts and their corrections are retained in `attempts/failed-debug-attempts.md`.

## Scope and limitations

All provider/response fixtures are synthetic. No live ChatGPT response, browser doorbell, production database/service, credentials or grants were used. No merge or deployment was performed. C4 PR #130 now accepts complete typed PlanStep objects (head `36895a70aa0ceb94c2d1dd1f20f91b410e656a3a` at evidence update); combined C2/C3/C4 acceptance remains pending. C2 still needs to inject its browser worker using the C3 `doorbell_worker` service seam. Canonical process graph updates are owned by W3 and are not claimed by this checkout. This is code-level isolated evidence, not live acceptance or component DONE.

<!--
Riverview Controlled Evidence
File: evidence/checkouts/RESIDENT-REASONING/20261018T2010Z-5c4a005/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Record C3 exact proposal review implementation and isolated verification
Execution Model: Disposable PostgreSQL 16 integration tests and mocked local provider tests
Observability: Test logs, revision audit, source commit, predecessor backup hashes
Dependencies: Python 3.12.3; PostgreSQL 16.15; repository unittest suite
Authority: Synthetic provider fixtures only; no production service, credentials, grants, browser or live ChatGPT
Changed: 2026-10-18 UTC | RV-C3-EXACT-PROPOSAL-REVIEW-001 | Capture exact-commit isolated acceptance evidence
Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md; docs/components/RESIDENT_REASONING.md
Tests: tests/test_external_reasoning_exchange.py; tests/test_resident_reasoning.py; tests/test_local_reasoning_provider.py
History: Git and .riverview-backups/manifest.jsonl
-->
# C3 exact proposal review checkout evidence

- **Task:** `RV-C3-EXACT-PROPOSAL-REVIEW-001`
- **Host/environment:** Camrui Ubuntu 24.04; isolated worktree `/home/admin1/projects/Riverview-Grace-Review-C3`
- **Branch:** `codex/c3-exact-proposal-review-20261018`
- **Source commit:** `5c4a00512e5acd6f72aa766ea866a8828184b151`
- **Base:** PR #119 head `97128626df967bc992696dca38eaa7116f3616e9`
- **PR:** https://github.com/ppow1/Riverview-/pull/135 (draft at evidence creation)
- **Run began (UTC): `2026-10-18T20:09:43Z`; final commands completed before this evidence commit.
- **Runtime versions:** Python 3.12.3; PostgreSQL 16.15; `pg_virtualenv` 16/regress temporary cluster.

## Commands and outcomes

1. `pg_virtualenv -t sh -c 'export RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER password=$PGPASSWORD"; PYTHONPATH=src python3 -m unittest tests.test_external_reasoning_exchange tests.test_resident_reasoning -v'` — exit 0; **33 passed, 0 failed**. The temporary cluster was dropped by `pg_virtualenv`. Covers exact subject digest/tamper, durable digest echo, Grace finish, revision 1→2→finish, successor restart recovery, response/claim fencing, authority, expiry/retry and existing resident regressions.
2. `PYTHONPATH=src python3 -m unittest tests.test_local_reasoning_provider -v` — exit 0; **31 passed, 0 failed**. Includes local prompt binding of subject and advisory as separate inputs.
3. `python3 -m compileall -q src/riverview_core` — exit 0.
4. `git diff --check HEAD^ HEAD` — exit 0.
5. `python3 scripts/revision_control.py check --baseline evidence/checkouts/RESIDENT-REASONING/20261018T2010Z-5c4a005/pre-edit-revision-baseline.json` — **PASS, zero findings**. The run used the pre-edit baseline snapshot recorded with this evidence.
6. Predecessor restore check — **10/10 PASS**: every backup file is retrievable, byte-identical to the source at the base commit, and matches its recorded SHA-256. See `predecessor-verification.log`.

Expected synthetic crash-injection tests emit only sanitized `failure_type: RuntimeError` event lines while asserting recovery; no prompt/advisory bodies or credentials are logged. Known failed debugging attempts and their corrections are retained in `attempts/failed-debug-attempts.md`.

## Scope and limitations

All provider/response fixtures are synthetic. No live ChatGPT response, browser doorbell, production database/service, credentials or grants were used. No merge or deployment was performed. Combined C2/C3/C4 testing remains blocked on C4 adapting its current string-step validator to C3's complete typed step objects. Canonical process graph updates are owned by W3 and are not claimed by this checkout. This is code-level isolated evidence, not live acceptance or component DONE.

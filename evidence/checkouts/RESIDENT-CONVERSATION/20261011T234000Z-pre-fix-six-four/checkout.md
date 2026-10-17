<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/RESIDENT-CONVERSATION/20261011T234000Z-pre-fix-six-four/checkout.md
Component: RESIDENT-CONVERSATION
File Revision: 1.0.0
Task: RV-M3.4-CHAT-DURABILITY-001
History: See artifacts.json and Git
-->
# Pre-fix exact event visibility reproduction

**Recorded:** 2026-10-11 UTC
**Pre-fix source:** `ea6748729fabfa3b93e3abb457f4e0e46357be26`
**Database:** Disposable PostgreSQL 16.15 cluster from `pg_virtualenv -t`; unique schema dropped by the test fixture.
**Provider:** Existing deterministic fake provider used by the repository's isolated integration fixture; no model endpoint contacted.

## Reproduction

The historical path shared one psycopg connection among request threads. The reproducer first commits two successful turns (four event rows). It then holds an outer transaction on that same connection to model another request having opened a transaction, calls the ordinary conversation service for a third turn, and reads history through the same connection before the outer scope exits. The service returns `completed`; its nested transaction has only released its savepoint, not committed the outer transaction. A separate PostgreSQL connection still sees four rows while the in-process history sees six. The shared connection is still `INTRANS`.

Exact sanitized result:

```json
{"api_ack_status":"completed","connection_in_transaction_before_outer_commit":true,"exact_six_vs_four_reproduced":true,"independent_postgresql_events":4,"preexisting_committed_events":4,"same_connection_api_events":6}
```

This controlled overlap demonstrates how interleaved request transaction ownership can produce the original visibility discrepancy and idle-in-transaction observation. It does not claim to recreate the exact timing of the original live request threads; the live incident measurements remain in `commissioning-summary.json` from the failed deployment.

## Reproduction command

```bash
git worktree add --detach /tmp/rv-grace-prechange-ea674 ea6748729fabfa3b93e3abb457f4e0e46357be26
PYTHONPATH=/tmp/rv-grace-prechange-ea674/src RIVERVIEW_TEST_PG_DSN='dbname=postgres' \
  pg_virtualenv -t python3 evidence/checkouts/RESIDENT-CONVERSATION/20261011T234000Z-pre-fix-six-four/reproduce.py \
  --repo /tmp/rv-grace-prechange-ea674
git worktree remove --force /tmp/rv-grace-prechange-ea674
```

The source checkout hash is enforced by the script. The test fixture creates and drops only its unique `rvtest_*` schema. No shared database or service is accessed.

The first command attempt occurred after the temporary worktree had already been removed; `git` returned “No such file or directory” before fixture setup. `pg_virtualenv` dropped its empty temporary cluster. The pinned worktree was recreated, the same evidence script then passed with the exact 6/4 result, and the temporary worktree was removed. This setup failure is retained in `reproduction-output.json`.

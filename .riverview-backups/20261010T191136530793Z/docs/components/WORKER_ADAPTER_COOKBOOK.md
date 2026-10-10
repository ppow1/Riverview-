# Riverview~ worker adapter cookbook

**Document Revision:** 1.0.4
**Component:** WORKER-ADAPTER
**Task:** RV-M2.1-001
**Status:** IN PROGRESS — disposable PostgreSQL only

## Isolated verification

The M2.1 fixture creates a unique `rvtest_*` schema on
`RIVERVIEW_TEST_PG_DSN`, applies M1.2, M1.4, and M2.1 migrations explicitly,
and drops only that schema. Never point it at shared `riverview_dev`.

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<disposable PostgreSQL DSN>' python3 -m unittest tests.test_worker_adapter -v
```

The tests verify authenticated scope-filtered dispatch and start,
token/capability/scope rejection, credential digest storage, deterministic
result persistence and replay, input collision rejection, unfinished-attempt
visibility, independent concurrent cycles, fail-closed evidence waiting,
timeout behavior, and durable grounding/preflight provenance.

Run the provider contract suite without PostgreSQL:

```bash
PYTHONPATH=src python3 -m unittest \
  riverview_core.worker_adapter.knowledge_provider_v1.test_contract -v
```

The default provider is unavailable and never authorizes a task. To test a fake
replacement, inject an object implementing all four methods from the versioned
[provider contract](../../src/riverview_core/worker_adapter/knowledge_provider_v1/README.md).
Only return `VERIFIED` with complete retrieval and source references. Otherwise
the worker records the result and sets that assignment's workflow step to
`WAITING_FOR_EVIDENCE`; the next `run_once()` can claim unrelated work.

The worker waits at most five seconds per provider call by default (configurable
per worker), caps in-flight provider calls at four per worker, discards late
results, and records timeout as `UNAVAILABLE`. Python cannot forcibly cancel an
in-process provider thread; a provider must use its own bounded network/storage
timeouts and tolerate concurrency. The interface has no fallback to invented
commands or contracts.

## Independent outcome verification

M2.2 verification tests apply migration 0003 only in the fixture's unique
`rvtest_*` schema. A separate worker-registry identity must have
`assignment.verify.v1` and the same authority scope; the executor identity is
rejected. `DeterministicSha256Verifier` checks the attempt state and artifact
against its recorded input and result digests. ACCEPTED evidence is stored
before the state transition, so a restart can safely retry the idempotent
transition. REJECTED results become `rework_required`; INCONCLUSIVE results
become blocked. The schema trigger prevents direct completion without accepted
evidence. The fixture drops the disposable schema after each test.

## Operational boundaries

M2.1 has no systemd worker service or network listener. The test credential is
kept in process memory and is not logged. Do not deploy this adapter until an
approved secret-delivery mechanism, worker process lifecycle, and operational
recovery procedure have been verified. An attempt left `running` is evidence of
incomplete work, not proof of whether a future external effect occurred. The
current built-in deterministic task has no external side effects.

## Failure and restart recovery (M2.3)

Before a custom action runs, the worker persists an execution intent with an
effect class. The built-in deterministic action is `retry_safe`; custom actions
default to `external_uncertain` and must not be marked retry-safe unless their
contract proves replay safety. An old `running` assignment with no intent is
conservatively uncertain.

At worker startup or a recovery polling boundary, call
`PostgresRecoveryCoordinator(dsn, schema=...).reconcile_expired()` after the
explicit worker-adapter migrations have been applied. The operation locks only
expired running assignments and records the decision with causal state events:

- A committed result is preserved and advances to `awaiting_verification`.
- A `retry_safe` unfinished action is marked for recovery, its old attempt is
  fenced as `lease_lost`, and the assignment passes through `blocked` to
  `ready`. The next claim increments its lease generation.
- An `external_uncertain` or legacy action moves to `awaiting_steward`. Never
  replay it until authoritative evidence resolves whether the effect occurred.

`worker_recovery_records` is the durable audit trail. Only assignments still in
`running` with an expired lease are selected, so completed/verified work is not
rewound. Review recovery records and external evidence before moving
`awaiting_steward` work forward. The PostgreSQL integration tests kill a real
worker subprocess after an isolated test effect commits; they do not constitute
service deployment or live operational commissioning.

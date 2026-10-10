# Riverview~ worker adapter cookbook

**Document Revision:** 1.0.3
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
current deterministic task has no external side effects.

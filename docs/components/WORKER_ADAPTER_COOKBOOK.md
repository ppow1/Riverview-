<!--
Riverview~ Controlled Document
File: docs/components/WORKER_ADAPTER_COOKBOOK.md
Component: WORKER-ADAPTER
File Revision: 1.0.9
Purpose: Diagnose isolated worker identity, attempt, verification and recovery records safely
Authority: Read-only diagnosis; credential delivery and worker enrollment are trusted control-plane operations
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS | Add redacted worker and verification record queries with failure interpretation
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-CROSS-BRANCH-DOC-PORT | Carry diagnostic query and recovery guidance into M3.3 package
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-CROSS-BRANCH-REVISION-ALIGNMENT | Align document revision metadata with the globally monotonic file revision
History: Git and revision backup manifest
-->
# Riverview~ worker adapter cookbook

**Document Revision:** 1.0.9
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

`ContinuousWorker.run_once()` invokes
`PostgresRecoveryCoordinator(dsn, schema=...).reconcile_expired()` before each
claim, after the explicit worker-adapter migrations have been applied. The
operation locks only expired running assignments and records the decision with
causal state events:

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

## Worker registration and persisted execution diagnosis

There is no commissioned always-on worker service or enrollment CLI in this
environment. `PostgresWorkerAdapter.register_worker()` is a trusted
control-plane operation, returns a bearer credential once, and stores only its
SHA-256 digest. Do not call it against shared `riverview_dev` as a diagnostic,
manually insert a worker row, or publish the returned credential. Enrollment
and credential transport must use the governed authority workflow and an
approved protected secret-delivery path. A registry row alone does not prove
that a worker process is running or capable of executing code.

The following inspection is for a disposable, fully migrated fixture schema
only. Use a protected `.pgpass` and set libpq's non-secret target variables to
the disposable test database. Replace `rvtest_worker` in each query with the
exact unique schema created by the fixture. Confirm the database identity and
the presence of all required relations before the detailed queries:

```bash
psql -X --set=ON_ERROR_STOP=1 -d "$PGDATABASE" -c \
  'BEGIN READ ONLY; SELECT current_database(), current_user; SELECT to_regclass($q$rvtest_worker.worker_registry$q$) AS worker_registry, to_regclass($q$rvtest_worker.worker_attempts$q$) AS worker_attempts, to_regclass($q$rvtest_worker.worker_results$q$) AS worker_results, to_regclass($q$rvtest_worker.verification_records$q$) AS verification_records, to_regclass($q$rvtest_worker.worker_execution_intents$q$) AS execution_intents, to_regclass($q$rvtest_worker.worker_recovery_records$q$) AS recovery_records; COMMIT;'
```

If a relation is `NULL`, stop before querying it and compare the target's
`schema_migrations` checksums with the explicit migration chain in the source
release. Do not create missing relations by hand or let an application startup
apply DDL. In shared `riverview_dev`, use the consolidated operations guide's
read-only inventory; this component's worker service and enrollment have not
been commissioned.

For the isolated fully migrated schema, inspect worker capability/active
metadata and bounded lifecycle records. These queries deliberately omit
credential digests, scope references, action inputs, event payloads, evidence
references, summaries, result JSON, and private content:

```bash
psql -X --set=ON_ERROR_STOP=1 -d "$PGDATABASE" -c \
  'BEGIN READ ONLY; SELECT worker_id,capabilities,active,registered_at FROM rvtest_worker.worker_registry ORDER BY registered_at,worker_id; SELECT attempt_id,assignment_id,worker_id,lease_generation,capability,status,started_at,finished_at,failure_class FROM rvtest_worker.worker_attempts ORDER BY started_at DESC,attempt_id DESC LIMIT 100; SELECT attempt_id,result_sha256,recorded_at FROM rvtest_worker.worker_results ORDER BY recorded_at DESC,attempt_id DESC LIMIT 100; SELECT verification_id,assignment_id,attempt_id,executor_id,verifier_id,verifier_revision,decision,recorded_at FROM rvtest_worker.verification_records ORDER BY recorded_at DESC,verification_id DESC LIMIT 100; SELECT intent_id,assignment_id,worker_id,lease_generation,capability,effect_class,status,attempt_id,started_at,finished_at,failure_class FROM rvtest_worker.worker_execution_intents ORDER BY started_at DESC,intent_id DESC LIMIT 100; SELECT recovery_id,assignment_id,lease_generation,decision,previous_state,resulting_state,observed_expiry,recorded_at FROM rvtest_worker.worker_recovery_records ORDER BY recorded_at DESC,recovery_id DESC LIMIT 100; COMMIT;'
```

Interpret the rows without promoting worker claims to verified completion:

| Observation | Interpretation | Safe response |
| --- | --- | --- |
| No active worker row | No eligible registered identity is visible; it does not imply worker health. | Check expected migration state and governed enrollment records. Do not create or activate a worker by direct SQL. |
| Inactive worker, missing capability, or scope mismatch | Authentication/dispatch is expected to fail closed. | Compare the authorized identity and assignment scope with the control-plane record; rotate/re-enroll only through its approved secret path. Never inspect or export `credential_sha256`. |
| `running` attempt without result | Work is incomplete; the external effect may be uncertain. | Inspect its matching execution intent and recovery record. Replay only a persisted `retry_safe` decision; `external_uncertain` or legacy work waits for evidence/escalation. |
| `succeeded` attempt/result without verification row | Executor-reported output has not been independently accepted. | Preserve the result digest and run an independently registered verifier with a different identity; do not mark the assignment complete. |
| `REJECTED` verification | Output failed the independent criteria. | Follow the durable rework transition and preserve the rejected evidence. Do not delete the record or rerun with the same identity as verifier. |
| `INCONCLUSIVE` or assignment `awaiting_steward` | Evidence is insufficient or the external effect cannot be safely resolved. | Keep it waiting and escalate with the exact assignment/attempt/recovery IDs; do not infer success or automatic replay. |
| `result_preserved` recovery record | A committed result was retained for verification. | Confirm the corresponding result digest and independent verification outcome. Recovery does not itself mean accepted completion. |

The integration suite covers enrollment credential hashing without printing the
token, scope/capability rejection, independent verification, forced worker
termination and restart recovery in isolated schemas:

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<disposable PostgreSQL test DSN>' \
  python3 -m unittest tests.test_worker_adapter -v
```

Expected: all database-backed worker tests execute with zero skips. Fixtures
create and remove their exact unique schema. If the process is interrupted,
list `rvtest_*` schemas and establish the exact owner/run before cleanup; never
use wildcard schema deletion. A schema/migration mismatch, old token accepted
after lease fencing, same executor/verifier accepted, unverifiable result
marked complete, unknown external effect automatically replayed, or unclear
fixture ownership is an escalation condition. Preserve all records and do not
repair by directly changing assignments, leases, attempts, or verifications.

## Revision history

- **1.0.9 — 2026-10-11:** Align document revision with the globally monotonic file revision.

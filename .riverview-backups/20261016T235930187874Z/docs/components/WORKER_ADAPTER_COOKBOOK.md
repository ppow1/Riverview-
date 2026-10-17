<!--
Riverview~ Controlled Document
File: docs/components/WORKER_ADAPTER_COOKBOOK.md
Component: WORKER-ADAPTER
File Revision: 1.0.14
Purpose: Diagnose worker identity, attempts, verification and recovery; retire the exact M33 registrations safely
Authority: Read-only diagnosis; retirement only through the fixed Steward-authorized M33 operation. Credential delivery and enrollment remain trusted control-plane operations.
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS | Add redacted worker and verification record queries with failure interpretation
Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Add bounded model execution and diagnosis steps
Changed: 2026-10-16 UTC | RV-WORKER-HEALTH-REPORTING-001 | Explain why lease-heartbeat freshness cannot determine idle worker process state.
Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Document the real isolated concurrent model acceptance and harness
Changed: 2026-10-11 UTC | RV-M3.3-WORKER-SERVICE | Document separate executor/verifier systemd preflight and recovery
Changed: 2026-10-11 UTC | RV-M3.3-LIVE-COMMISSIONING | Link confirmed Camrui deployment evidence and distinguish verified queue recovery from concurrency
Changed: 2026-10-11 UTC | RV-M3.3-WAITING-ISOLATION | Link the live NO_MATCH and scheduler-continuation evidence
Changed: 2026-10-11 UTC | RV-M3.3-WAITING-ISOLATION-LINK-CLARIFICATION | Present checkout evidence as a non-linked path in dashboard-served documentation
Changed: 2026-10-11 UTC | RV-M3.3-WAITING-ISOLATION-REVISION-CORRECTION | Add the missed controlled file revision increment for the preceding same-task content edits
Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001-GUARD-DOCS | Require fresh action preflight and remaining retry budget for grounded resume
Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Link the guarded M33 worker-registration retirement lifecycle and failure handling
Changed: 2026-10-11 UTC | RV-M3.3-WAITING-ISOLATION-LINK-CLARIFICATION | Present checkout evidence as a non-linked path in dashboard-served documentation
History: Git and revision backup manifest
-->
# Riverview~ worker adapter cookbook

**Document Revision:** 1.0.10
**Component:** WORKER-ADAPTER
**Task:** RV-M2.1-001
**Status:** IN PROGRESS — disposable PostgreSQL only

## Retire the revoked M33 commissioning registrations

Do not directly update or delete `worker_registry` rows. For the one revoked M33
run `e92ec51590b34cd3b04d05c000f3eab4`, use the fixed root-local operation in
[`M33 worker registration retirement`](../development/M33-WORKER-REGISTRATION-RETIREMENT-20261016.md).
It requires an active Steward `identity.manage` institution grant, a revoked
run state record, all three M33 units stopped, revoked worker grants and
credentials, and no live M33 lease or executable assignment. The transaction
preserves all historical rows and appends two authority events. Any mismatch
fails closed. Production execution is separate from source implementation and
requires migration 0009 plus captured operator pre/postflight evidence.

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

### Evidence restored after `WAITING_FOR_EVIDENCE`

The persistent Codex worker can resume the same assignment after fresh source
grounding becomes `VERIFIED`; it does not create a new objective or assignment.
Candidate selection authenticates the worker's current exact grant and scope.
The atomic recovery event is written only when the assignment is still blocked
at `WAITING_FOR_EVIDENCE`, its lease is absent or expired, objective evidence
remains verified, grounding and action preflight are freshly `VERIFIED`, and no
attempt, result, verifier record, assignment artifact, running/unknown intent,
or unreconciled Codex intent exists. Prior Codex intents must each have typed
failure provenance and a `retry_safe` recovery record. The configured retry
ceiling applies. The event retains both source revisions, digests, references,
and canonical ready-node identity. The normal claim checks the grant again
before execution.

Read-only diagnosis for one known assignment (replace only the literal
assignment ID with an already authorized ID): inspect `assignments.state`,
`workflow_step`, `process_graph_id`, `process_node_id`; the latest
`knowledge_observations` status/revision/digest; lease expiry; execution-intent
statuses/failure classes; recovery decisions; attempts/results/verifications;
and the assignment-bound artifact's metadata. Do not select objective request,
conversation, prompt, or artifact contents for this metadata check. If the
latest fresh grounding is not `VERIFIED`, any intent is unknown, a result or
artifact exists, the lease is active, or authority is denied, leave the item
blocked and follow its existing evidence/escalation route. Never change the
assignment row by direct SQL.

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
| Active registration with no recent lease heartbeat | There is no current assignment-lease heartbeat to classify. An idle continuous poll loop does not own a lease, so this alone does not establish that the process is idle, disconnected, blocked, or failed. | Check service process and safe logs through authorized host access, then correlate with attempts, scheduler leases, and event processing. The dashboard does not report process liveness. Do not restart a production worker as a diagnostic step. |
| Stale latest lease heartbeat and no active lease | The last lease heartbeat is old; current worker process state is not represented by this projection. | Inspect authorized read-only service and journal state and lease/attempt history. A stale lease signal alone is not proof that the worker process failed. |
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

## Supervised M3.3 executor and verifier services

The versioned units are
`deploy/systemd/riverview-m33-worker.service` and
`deploy/systemd/riverview-m33-verifier.service`. They are source definitions;
check the deployment record before claiming a unit is active. Camrui live
commissioning evidence for source `47a79adafe1524b3e819148b70c02a1857f50dbf`
is retained in
[`M3.3 live evidence`](../development/M3.3-001_REVISION_RECORD.md) and
`evidence/checkouts/M3.3-LIVE-E2E/20261011T1245Z-47a79ad/`. At the evidence
capture, the governed intake, executor, verifier, event processor, CME monitor,
notification dispatcher, and dashboard were active. The evidence demonstrates
an authorized repository-test assignment, independent verification, artifact
persistence, and safe queue recovery after restart. A separate live probe persisted an assignment with missing repository evidence as
`WAITING_FOR_EVIDENCE`; while it remained there, the scheduler completed a valid
assignment through artifact creation and independent verification. See checkout
evidence at
`evidence/checkouts/M3.3-WAITING-ISOLATION/20261011T1310Z-47a79ad/acceptance.json`.
This proves waiting work does not block unrelated eligible work. It does not
claim simultaneous executor-process throughput. Scoped technical criteria are
ready for Steward review; full Component DoD and formal acceptance remain open. The executor uses the fixed `deterministic.sha256.v1`
capability and repository-backed provider pinned to an exact committed release.
The verifier is a separate service identity and `assignment.verify.v1` worker.
Both use root-owned systemd credential sources and PID 1 credential delivery;
the bearer itself is never an environment variable, command argument, log, or
database plaintext. The worker account cannot modify installed release bytes.

Read-only service preflight:

```sh
systemctl status riverview-m33-worker.service riverview-m33-verifier.service --no-pager
journalctl -u riverview-m33-worker.service -u riverview-m33-verifier.service -n 100 --no-pager
systemctl show riverview-m33-worker.service riverview-m33-verifier.service \
  --property=User,FragmentPath,ExecStart,LoadCredential,Restart --no-pager
```

Expected identities are `riverview`; both units have private PostgreSQL
credentials, and executor/verifier bearer files are different. A missing unit,
expired exact grant, missing schema or package pin must fail closed. Inspect
`worker_registry` without the digest:

```sql
BEGIN READ ONLY;
SELECT worker_id,capabilities,scope_ref,active,registered_at
FROM riverview_dev.worker_registry ORDER BY worker_id;
SELECT principal_id,action,scope_ref,valid_until,revoked_at
FROM riverview_authority.authority_grants
WHERE action IN ('worker.register','assignment.execute','assignment.verify')
ORDER BY principal_id,action,scope_ref;
COMMIT;
```

Check only the exact commissioning scope. Never print token files, inspect
`credential_sha256`, copy credentials to shell variables, or grant wildcard
scope. If the current registered identity, token digest, capabilities or scope
differs from protected configuration, the service must remain stopped until
Steward enrollment is reconciled through the authority API.

Restarting either exact unit is non-destructive and reuses the persisted worker
identity and attempt state:

```sh
sudo systemctl restart riverview-m33-worker.service
sudo systemctl restart riverview-m33-verifier.service
```

After restart, confirm a fresh systemd process, a healthy dashboard worker
projection, stable assignment/attempt IDs, no duplicate result or verification,
and a valid pinned source revision. A successful process restart alone is not
proof that a task was resumed or accepted. Do not manually change assignments,
leases, authority grants, worker rows, artifacts, or verification rows to
recover a failure.


## Local inference worker (M4.3)

The worker action is `local.inference.v1`; registration, assignment authority,
verified knowledge preflight, lease fencing, durable intent, and independent
verification remain required. `LocalInferenceAction` accepts only a literal
loopback HTTP URL ending in `/v1`, for example `http://127.0.0.1:8767/v1`. It
rejects public/private network hosts, DNS names, embedded user-info, query
strings, and non-HTTP schemes. The action sends a bounded grounded prompt,
rejects credential-shaped content, allows at most 90 seconds and 128 generated
tokens by default, and rejects
truncated, malformed, empty, or oversized responses. Error values are sanitized
and omit request/response bodies.

For the pinned CPU commissioning experiment, the llama.cpp server was built
from upstream tag `v0.6.0` at commit
`d81235049384534c167caea52b85a694f6103d14`; Qwen3-0.6B-GGUF was downloaded
from immutable model revision
`23749fefcc72300e3a2ad315e1317431b06b590a`. Model file SHA-256 must match
`9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`. Keep
these weights outside the source repository. The server is temporary and
loopback-bound; no inference systemd unit is installed by this commissioning
procedure. See the M4.3 revision record for exact commands, live runtime
measurements, durable assignment/attempt/result/verification IDs, and cleanup.

Run the committed `scripts/verify_local_inference.py` only with the private
UTF-8 PostgreSQL test cluster, the pinned executable and model, and a new
evidence-directory path. The harness validates the DSN and model checksum,
creates one unpredictable `rvtest_m43_*` schema, applies the checked-in
migrations, executes two separate workers concurrently, verifies each saved
artifact with a different identity, then stops its own loopback server and
drops only the schema it created. Its fixture knowledge source contains two
fixed instruction tasks; it is not an institutional knowledge provider. The
acceptance checks instruction following, durable persistence, result hashes,
independent decisions and real overlapping model calls—not general reasoning
quality. Preserve failed-run evidence and investigate it before retrying.

Example command (all paths and the test DSN must refer to the verified private
test setup):

```bash
PYTHONPATH=src python3 scripts/verify_local_inference.py \
  --dsn "$RIVERVIEW_TEST_PG_DSN" \
  --server /tmp/rv-llama-build/bin/llama-server \
  --model "$HOME/.cache/riverview/models/Qwen3-0.6B-Q8_0.gguf" \
  --output evidence/checkouts/M4.3-LOCAL-INFERENCE/<new-run-id>
```

### Diagnosis

| Symptom | Diagnostic | Expected result / interpretation | Safe action | Escalate when |
|---|---|---|---|---|
| `endpoint_unavailable` | `ss -ltn '( sport = :8767 )'; curl --fail --silent --show-error --max-time 3 http://127.0.0.1:8767/health` | Listener is loopback-only and model health is ready; connection failure is not a worker success | Start the exact pinned local server only for the isolated commissioning run; retry the assignment after readiness | Port ownership differs, listener is non-loopback, model file checksum differs, or process exceeds the bounded memory budget |
| HTTP status error | Inspect only sanitized exception class and server process exit status; do not save prompt/server request logs | Endpoint returned a non-success status; `LocalInferenceError` has no body | Correct server readiness or stop the test; retain assignment failure and use the worker's normal retry/recovery policy | Repeated 4xx/5xx after verified readiness or unexpected network destination |
| `response_schema_invalid` / `response_incomplete` | Read no private response body from journal; validate configured API compatibility with a non-sensitive probe | A malformed or truncated response is rejected before durable success | Fix server/model/API version; the failed intent stays visible and no successful result is recorded | Runtime output differs from the pinned API contract or any incomplete output is accepted |
| Assignment waiting or blocked | Query the isolated database's attempt, intent and knowledge status using the worker cookbook's redacted queries | Missing VERIFIED grounding/preflight or failed model calls remain non-success | Correct only the missing dependency and run the assignment again through normal lease/recovery flow | A missing provider/authority response is represented as successful or a lease is bypassed |
| Result exists without accepted verification | Inspect persisted artifact digest, attempt and verification rows using the isolated read-only query | Executor output remains unverified until another identity accepts it | Run the distinct authorized verifier against the stored artifact; preserve rejected evidence | The executor can self-verify or completed state appears without accepted evidence |

To stop the temporary runtime after acceptance, terminate only the recorded
llama-server PID, confirm port 8767 is closed, and verify the PostgreSQL test
cluster's cleanup separately. Do not kill by a broad `pkill` pattern. The local
inference call has no remote side effects; keep action `retry_safe`, while future
network tools must declare `external_uncertain` until their contract proves
otherwise.

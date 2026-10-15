<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_REASONING_COOKBOOK.md
Component: RESIDENT-REASONING
File Revision: 1.0.1
Purpose: Diagnose and safely recover resident grounding and provider routing
Authority: Read-only checks first; proposals never grant action authority
Changed: 2026-10-11 UTC | RV-M4.2-001 | Add M4.2 isolated runtime troubleshooting procedure
Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-CONTEXT-001 | Diagnose missing resident grounding contract reference
History: Git and .riverview-backups/manifest.jsonl
-->
# Resident reasoning operations cookbook

**Current state:** isolated PostgreSQL-backed implementation only. Camrui has
no dedicated authority registry schema or resident reasoning service. Never
point the test DSN at shared `riverview_dev`; never place the resident token,
manager DSN, or model secret in a command, log, or evidence artifact.

## Symptoms and diagnostics

| Observable result | Likely cause | First safe action |
|---|---|---|
| `AUTHORITY_DENIED / OFFICE_STATE_GRANT_REQUIRED` | Missing, revoked, expired, or wrong office scope | Do not invoke provider. Inspect exact office binding and grant metadata using the read-only queries in `INSTITUTIONAL_AUTHORITY_COOKBOOK.md`. Steward must issue the exact grant; never insert it with SQL. |
| `WAITING_FOR_EVIDENCE / GROUNDING_NOT_VERIFIED` | Knowledge provider is unavailable, incomplete, contradictory, stale, or has no match | Inspect the durable office-state outcome summary: grounding and regrounding statuses, references, revision/hash and trigger. Do not replace the status with verified manually. |
| `GROUNDING_NOT_VERIFIED` with both statuses `NO_MATCH` and empty provider references | The durable objective context may omit `repo://riverview/resident-engineering.v1`, routing lookup to the generic provider | Check the context contract reference in `GraceExecutionPipeline.read_reasoning_context`; restore the exact constant and verify the pinned resident source set. Do not alter the objective evidence or mark the outcome verified manually. |
| `WAITING_FOR_EVIDENCE / KNOWLEDGE_NOT_SERIALIZABLE` | Provider returned data outside its JSON result contract | Record provider ID and outcome code; repair the provider contract adapter, then reground. |
| `WAITING_FOR_EVIDENCE` with assignment context error | Reader returned wrong assignment ID, missing revision, credential-shaped field, or input over 32 KiB | Read only the assignment's approved metadata projection. Remove secrets at the source boundary; do not broaden the redaction allowlist without review. |
| `UNAVAILABLE / PROVIDER_ROUTE_UNAVAILABLE` | Active `provider_ref` is not registered or explicit fallback config is invalid | Compare the office binding's implementation/provider revision with the in-memory registry. Configure only a reviewed provider ID and explicit fallback. |
| `UNAVAILABLE / PROVIDER_TIMEOUT_OR_FAILURE` | Every explicitly allowed provider timed out or raised | Inspect provider health and timeout counters. A timed-out daemon remains bounded by the process-wide slot cap until it exits. Restore provider health; do not raise the cap to hide a leak. |
| `INVALID_PROPOSAL / PROPOSAL_SCHEMA_OR_BUDGET` | Provider output type/step graph is invalid or exceeds per-attempt token allotment | Retain request ID/provider ID and repair the adapter; output is not persisted as a plan. Do not route an invalid proposal to execution. |
| `STALE_CONTEXT` | Office implementation/binding or assignment revision changed during provider execution | Discard the returned output. Reload current authoritative context and call again with a new trigger/request ID. Never force the old plan into state. |
| `STATE_CONFLICT` | Concurrent office-state writer changed the expected revision or state exceeded its bound | Read current office revision and current resident state; preserve both writers. Reconcile using a new context load and fresh proposal. Never blind-retry a stale write. |
| `UNAVAILABLE / OFFICE_STATE_STORE_UNAVAILABLE` | Registry database unavailable | Follow PostgreSQL and authority registry diagnosis. Do not fall back to in-memory authority or accept provider success as durable. |

## Isolated verification

Use the project's private socket-only PostgreSQL test harness. The direct
component command is:

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<private disposable PostgreSQL test DSN>' \
  python3 -m unittest tests.test_resident_reasoning -v
```

Expected: all tests pass with zero skips. The fixture applies the standalone
authority migration chain to a unique fresh schema, creates a synthetic
Steward/resident/office/binding/grant, verifies persisted state, and drops only
that schema. After the suite, query the **disposable test database**:

```sql
SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'rvtest_%';
SELECT count(*) FROM pg_roles WHERE rolname LIKE 'rvtest_%';
```

Both values must be zero. Never run the suite against the commissioned
`riverview` database or use shared data for failure injection.

## Safe recovery and escalation

After a provider or registry recovery, create a new `ResidentReasoner` and
re-read current binding, office state, assignment revision, and verified
grounding. The prior plan is context only. Confirm the stored outcome has the
new request ID, current revisions, source references and provider ID. A
`PROPOSED` result is still not an approved assignment, successful execution, or
independently verified artifact.

Escalate if the registry role/schema ownership is uncertain, grant or binding
events conflict, checksums differ, credentials are lost, context cannot be
regrounded, or a proposal would need to mutate CME/assignment state. Do not
restart or modify the live dashboard/CME to repair an isolated resident test.

See the [authority cookbook](INSTITUTIONAL_AUTHORITY_COOKBOOK.md),
[worker knowledge contract](../../src/riverview_core/worker_adapter/knowledge_provider_v1/README.md),
and [resident reasoning contract](RESIDENT_REASONING.md).

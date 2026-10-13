<!--
Riverview~ Controlled Document
File: docs/components/GRACE_PERSISTENT_EXECUTION.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.0
Purpose: Define persistent model-independent Grace objective execution service
Authority: Existing exact-grant registry and CME assignment/worker contracts
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Define supervised reconciliation and dashboard interfaces
-->
# Grace Persistent Execution Service

**Status:** Implemented and integration-tested on isolated PostgreSQL; not installed or commissioned on Camrui. This service deliberately does not supply a reasoning model.

## Components and lifecycle

`GraceExecutionService` repeatedly reconciles already durable objective proposals. The dashboard accepts an objective only with its authenticated dashboard session **and** an `objective.submit` exact-grant credential. Repository grounding is pinned and fail-closed. A typed proposal is persisted separately; a proposal alone does not grant authority. Dispatch uses the service's `assignment.create` credential for one configured scope, then the existing event processor owns queued-to-ready transitions, the leased `ContinuousWorker` owns execution, and the separately registered verifier owns acceptance. The service marks an objective complete only after a persisted ACCEPTED verification and a completed assignment.

The supervised poll has no run-once exit. It records a durable `grace_execution_health` row and continues after assignment-local worker failures. PostgreSQL remains the work source. A process restart reconstructs work from objective, assignment, lease, attempt, result, and verification rows; stable objective-derived assignment IDs and ledger idempotency keys prevent duplicate handoff. Existing worker execution-intent recovery fences interrupted attempts; the Grace runner caps dispatch authorization failures at three durable retries. Unknown external effects remain governed by the worker recovery contract.

## HTTP contract

All `/api/v1` operations require `Authorization: Bearer <dashboard credential>`. This credential grants dashboard access only.

| Method and route | Additional authorization | Request / response |
| --- | --- | --- |
| `POST /api/v1/objectives` | `X-Riverview-Authority` carrying exact `objective.submit` grant for `scope_ref` | JSON `{objective_id, request, acceptance_criteria, scope_ref}`. Returns 202 with `RECEIVED`, `GROUNDED`, or `WAITING_FOR_EVIDENCE`. Body limit 16 KiB; request/evidence limits remain pipeline-enforced. |
| `POST /api/v1/objectives/{id}/proposal` | Dashboard credential plus exact `assignment.create` grant for objective scope | JSON `{summary, steps:[{step_id, objective, acceptance_criteria, depends_on}], tokens_used}`. Returns 202 once the existing PlanProposal validation and full human criteria checks pass. |
| `POST /api/v1/objectives/{id}/cancel` | `X-Riverview-Authority` carrying exact `assignment.cancel` grant in the same scope | JSON `{scope_ref}`. Only the existing pre-execution queued/ready cancellation is allowed. |
| `GET /api/v1/objectives?limit=N` | Dashboard credential | Bounded objective, assignment state, artifact digest/reference, verifier decision, and source revision projection. |
| `GET /api/v1/objectives/{id}` | Dashboard credential | Same projection for one objective. |
| `GET /api/v1/status` | Dashboard credential | Includes Grace service instance, status, heartbeat age, last cycle, cycle count, and sanitized error type when its health migration is present. |

API errors never log request text or credentials. Missing/invalid exact grants return 403; missing migrations/provider data remain unavailable or WAITING_FOR_EVIDENCE, never verified. The separate exact grant is not persisted in ordinary events.

## Worker contract and retry behavior

The service is configured for one exact `work-order:` scope, a registered executor with `engineering.bounded-artifact.v1`, and a distinct verifier with `assignment.verify.v1`. Its only current worker action writes one assignment-derived JSON artifact in a private 0700 workspace; no shell command, caller-supplied path, model, or arbitrary code execution is available. Artifact bytes are reopened and checked independently before acceptance.

The default runner sets three persisted dispatch failures, three persisted retry-safe lease recoveries, and three persisted verifier invocation failures per attempt before leaving work for operator review. Retry exhaustion and verifier failures remain visible in objective projections. The execution retry ceiling is enforced by the worker recovery coordinator and its `retry_exhausted` record; no retry count is stored only in process memory. Verifier failures are isolated per candidate, so one malformed result cannot starve other assignments in a poll. Side effects of this bounded artifact action are idempotent by assignment and content. Other capabilities must supply their own effect classification and recovery contract. Cancellation uses the pre-execution exact-grant pipeline path. A running action is never force-cancelled.

## Runtime configuration and commissioning boundary

`deploy/systemd/riverview-grace-execution.service` is a versioned unit template. It expects protected systemd credentials named `pgpass`, `dispatch-token`, `worker-token`, and `verifier-token`, plus a root-owned `/etc/riverview/grace-execution.env` containing non-secret worker/verifier IDs, exact scope and a full approved repository commit. Required migrations must be applied by the controlled deployment procedure; the service never applies DDL automatically. This change does not install the unit, create credentials/grants, or alter the live Camrui services/database.

Read-only diagnosis:

```sh
systemctl show riverview-grace-execution.service -p ActiveState -p SubState -p MainPID
journalctl -u riverview-grace-execution.service --since=-15m --no-pager
psql "$RIVERVIEW_READONLY_DSN" -X -v ON_ERROR_STOP=1 -c "SELECT service_id,status,last_heartbeat_at,last_cycle_at,last_error_type,cycles_completed FROM riverview_dev.grace_execution_health"
```

Expected service status is `healthy`, with `last_heartbeat_at` newer than the dashboard stale threshold. A missing/stale row is not healthy. `last_error_type` contains only a class name. On service failure, inspect the journal and health row, verify unit credential ownership/permissions and exact grants without printing token contents, correct the underlying configuration, then use the authorized systemd restart procedure. Never delete objective, assignment, attempt, event, or verification rows to recover. Resume is automatic from durable state after the service starts.

## Verification and limitations

The integration test uses an isolated PostgreSQL schema, temporary Git repository, local HTTP server, deterministic typed proposal, existing bounded worker, and a separate verifier identity. It demonstrates denied and authorized intake, persisted grounding/proposal, authorized dispatch, restart reconstruction, one artifact/attempt, independent acceptance, durable objective completion, dashboard readback, and service heartbeat. This is test evidence only. The service is not yet live-commissioned; no real inference, general coding executor, browser Steward session, service restart on Camrui, systemd credential provisioning, or repeated unattended operational run is claimed.

Canonical graph: `process_graphs/grace/operational-integration.json`. Generated views are updated with `python3 scripts/process_graph.py generate`; validate with `python3 scripts/process_graph.py check` and `python3 scripts/process_graph.py validate`.

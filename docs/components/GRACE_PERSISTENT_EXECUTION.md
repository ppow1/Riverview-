<!--
Riverview~ Controlled Document
File: docs/components/GRACE_PERSISTENT_EXECUTION.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.5
Purpose: Define persistent model-independent Grace objective execution service
Authority: Existing exact-grant registry and CME assignment/worker contracts
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-CONFIG-EXAMPLE | Add a secret-free environment template for exact service identity configuration
Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Bind persistent reasoning to current office identity and durable office state
Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Use exact-grant office-state functions through the restricted runtime role
-->
# Grace Persistent Execution Service

**Status:** Persistent office-bound reasoning integration is isolated-test verified; service is not installed or commissioned on Camrui. Model calls remain optional and must match the active office implementation binding.

## Components and lifecycle

`GraceExecutionService` reconciles durable grounded objectives and proposals. When configured with the existing `ResidentReasoner`, the runner authenticates its resident credential against the exact `office.state.write` grant for `office:<office_id>` and requires a bound office occupant and implementation. The reasoner loads and CAS-writes office-keyed state, rechecks the current binding before persistence, and only produces a typed proposal. The objective adapter exposes only complete VERIFIED evidence and a durable objective revision. A proposal alone does not grant authority. Dispatch separately uses the service's `assignment.create` credential for one configured scope; the existing event processor owns queued-to-ready transitions, the leased `ContinuousWorker` owns execution, and the separately registered verifier owns acceptance. The service marks an objective complete only after a persisted ACCEPTED verification and a completed assignment.

The supervised poll has no run-once exit. It records a durable `grace_execution_health` row and continues after assignment-local worker failures. PostgreSQL remains the work source. A process restart reconstructs work and office identity from objective, assignment, lease, attempt, result, verification, office binding, grants, and office-state rows; stable objective-derived assignment IDs and ledger idempotency keys prevent duplicate handoff. Occupant replacement revokes the old exact office-state grant while preserving office-keyed plans. A restarted service loads the replacement credential; the reasoner rejects the former credential and rechecks the active binding before persistence. Existing worker execution-intent recovery fences interrupted attempts; the Grace runner caps dispatch authorization failures at three durable retries. Unknown external effects remain governed by the worker recovery contract.

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

`deploy/systemd/riverview-grace-execution.service` is a versioned unit template. It expects its own immutable `/opt/riverview-grace-execution/current` release containing this runner and package source, and uses the existing `/opt/riverview-core/.venv` Python environment. The independent release path is deliberate: the older `/opt/riverview-m33/current` release cannot supply M4.4 code. It expects protected systemd credentials named `pgpass`, `dispatch-token`, `worker-token`, `verifier-token`, and `resident-token`, plus a root-owned `/etc/riverview/grace-execution.env` containing the resident office ID, non-secret worker/verifier IDs, exact scope and a full approved repository commit. The authority schema must already have migrations 0000–0003 and the boundary helper must grant the runtime role only `USAGE`, exact-grant authorization, and the two bound office snapshot/CAS functions. The runner uses `AuthorityRegistry(runtime_safe=True)` and does not require manager-table privileges; functions recheck the `office.state.write` grant and active occupant under the office binding lock. Local reasoning is configured only as an all-or-none endpoint/model/SHA tuple; the existing provider enforces loopback and exact implementation-SHA binding. The secret-free key template is `deploy/grace-execution.env.example`; identities must already have their narrowly scoped grants. Required migrations must be applied by the controlled deployment procedure; the service never applies DDL automatically. This change does not install the unit, create credentials/grants, or alter live Camrui services/database.

Read-only diagnosis:

```sh
systemctl show riverview-grace-execution.service -p ActiveState -p SubState -p MainPID
journalctl -u riverview-grace-execution.service --since=-15m --no-pager
psql "$RIVERVIEW_READONLY_DSN" -X -v ON_ERROR_STOP=1 -c "SELECT service_id,status,last_heartbeat_at,last_cycle_at,last_error_type,cycles_completed FROM riverview_dev.grace_execution_health"
```

Expected service status is `healthy`, with `last_heartbeat_at` newer than the dashboard stale threshold. A missing/stale row is not healthy. `last_error_type` contains only a class name. On service failure, inspect the journal and health row, verify unit credential ownership/permissions and exact grants without printing token contents, correct the underlying configuration, then use the authorized systemd restart procedure. Never delete objective, assignment, attempt, event, or verification rows to recover. Resume is automatic from durable state after the service starts.

## Verification and limitations

The integration tests use isolated PostgreSQL schemas, a temporary Git repository, local HTTP server, deterministic typed proposal, existing bounded worker, and a separate verifier identity. They also compose `ResidentReasoner` with the persistent service across service reconstruction and occupant replacement: office plans remain durable, the replacement provider receives prior office state under the new binding revision, the old exact grant is denied, and the replacement plan becomes current. This is isolated evidence only. The service is not live-commissioned; no real inference, general coding executor, browser Steward session, service restart on Camrui, systemd credential provisioning, or repeated unattended operational Grace run is claimed.

Canonical graph: `process_graphs/grace/operational-integration.json`. Generated views are updated with `python3 scripts/process_graph.py generate`; validate with `python3 scripts/process_graph.py check` and `python3 scripts/process_graph.py validate`.

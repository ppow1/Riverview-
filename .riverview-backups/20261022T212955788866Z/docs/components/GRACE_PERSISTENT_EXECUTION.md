<!--
Riverview~ Controlled Document
File: docs/components/GRACE_PERSISTENT_EXECUTION.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.23
Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Document lifecycle criteria, ready-work-first cycle order, and Grace's durable completion decision
Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Integrate generation-aware review recovery with active operational diagnostics.
Changed: 2026-10-19 UTC | RV-C1-GRACE-RESULT-RECEIPT-001 | Source the durable publication acknowledgement cycle from the persisted result outbox
Purpose: Define persistent model-independent Grace objective execution service
Authority: Existing exact-grant registry and CME assignment/worker contracts
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-CONFIG-EXAMPLE | Add a secret-free environment template for exact service identity configuration
Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Bind persistent reasoning to current office identity and durable office state
Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Use exact-grant office-state functions through the restricted runtime role
Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Bind router-backed proposals and idempotent verified-result return to persistent execution
Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Add persistent no-copy Codex owner-session service mode and reauthentication behavior
Changed: 2026-10-15 UTC | RV-GRACE-CODEX-SANDBOX-READINESS-001 | Fail Codex worker preflight when the host cannot provide its required workspace sandbox
Changed: 2026-10-15 UTC | RV-GRACE-HEALTH-WRITER-ACL-001 | Specify the least-privilege heartbeat writer grant for the restricted runtime role
Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Reconcile dependency-ordered assignments through the existing lease and verifier lifecycle
Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Persist per-step assignments and model-reviewed same-objective continuation
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-SYSTEMD-NETLINK-001 | Restrict address-family addition to AF_NETLINK and preflight bubblewrap network namespace setup
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-ENABLE-001 | Pass --enable code_mode and --enable code_mode_host, and expose the pinned package directory for companion discovery
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-MDWE-001 | Disable MDWE only on the owner-session unit because its Code Mode host requires executable-memory mappings; retain offline bubblewrap workspace isolation
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-OWNER-STATE-001 | Keep writable Codex runtime state service-local and bind only the existing owner auth file read-only
Changed: 2026-10-16 UTC | RV-GRACE-OWNER-CODEX-HOME-001 | Resolve persistent Codex home from explicit service configuration and validate its private bind target
Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-GENERATIONS-001 | Define append-only evidence revision and bounded per-cycle review generations
Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-GENERATIONS-001 | Clarify generation-aware outbox acknowledgment and re-review recovery
Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Consume durable external reasoning replies through the existing reasoner and preserve stale-base successor completion semantics.
Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Admit configured model-selected advisory exchanges through active-resident exact grants and the existing CME cycle.
Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Resume the latest verifier rejection through Grace's bounded decision and expose durable progress in Talk with Grace.
-->
# Grace Persistent Execution Service

## Rejected work and durable conversation progress

When independent verification rejects a successful attempt, Grace reviews the latest decision on the next owner-session cycle. She may propose a bounded correction against the persisted criteria or request Steward direction. Rework preserves the original objective, assignment, acceptance criteria, artifact, and rejected verification record. The exact assignment creation grant is rechecked before the existing assignment is requeued, and the scheduler's previous lease generation is fenced. Every subsequent attempt is independently verified; repeated rejection is not silently treated as success.

Talk with Grace reads the existing authenticated `GET /api/v1/objectives?conversation_id=<uuid>` projection. The durable `objective.received` source binds each receipt to its conversation and source message sequence. The response summarizes lifecycle stage, assignment ID/state, latest event time, verifier decision/reason, rework count/status, and explicit Steward-action requirement. The dashboard polls while the conversation is visible and reloads from PostgreSQL after reconnect or page refresh; it does not infer progress from chat response text. The projection excludes conversation bodies, worker artifact contents, and credentials.

**Status:** Source integration of external exchange consumption and stale-base successor handling is isolated-PostgreSQL verified. Production release activation and live provider/rework acceptance remain unverified; service readiness must be checked against current systemd state.

## Components and lifecycle

`GraceExecutionService` reconciles durable grounded objectives and proposals. When configured with the existing `ResidentReasoner`, the runner authenticates its resident credential against the exact `office.state.write` grant for `office:<office_id>` and requires a bound office occupant and implementation. The reasoner loads and CAS-writes office-keyed state, rechecks the current binding before persistence, and only produces a typed proposal. The objective adapter exposes only complete VERIFIED evidence and a durable objective revision. A proposal alone does not grant authority. Dispatch separately uses the service's `assignment.create` credential for one configured scope; the existing event processor owns queued-to-ready transitions, the leased `ContinuousWorker` owns execution, and the separately registered verifier owns artifact integrity and acceptance. For conversation-origin objectives, persisted ACCEPTED verification is necessary but not sufficient: Grace must review verifier evidence and record `OBJECTIVE_COMPLETE` for that same completion cycle before the objective is completed.

The supervised poll has no run-once exit. It records a durable `grace_execution_health` row and continues after assignment-local worker failures. PostgreSQL remains the work source. A process restart reconstructs work and office identity from objective, step, assignment, lease, attempt, result, verification, office binding, grants, and office-state rows; stable per-step assignment IDs and ledger idempotency keys prevent duplicate handoff. Occupant replacement revokes the old exact office-state grant while preserving office-keyed plans. A restarted service loads the replacement credential; the reasoner rejects the former credential and rechecks the active binding before persistence. Existing worker execution-intent recovery fences interrupted attempts; the Grace runner caps dispatch authorization failures at three durable retries. Unknown external effects remain governed by the worker recovery contract.

When the external-reasoning provider map is explicitly configured, the same persistent cycle checks the existing durable exchange for response-received IDs. Grace rechecks `resident.reasoning.escalate`, consumes one fenced advisory response, and supplies it separately from verified knowledge to the bound resident reasoner. Proposal persistence and its correlated external-advisory evaluation event commit together before the exchange is acknowledged. If the service restarts after proposal persistence but before acknowledgement, the durable event is the idempotency fence and the pending exchange is acknowledged without a duplicate proposal. `request_external_reasoning()` persists an authorized exchange with conversation/objective lineage and a finite deadline without waiting on the provider. The exchange never approves or dispatches work.

The same service cycle initiates an exchange when the bound local reasoning provider returns a typed optional external escalation intent, selected from the configured external-provider map. The service reads the originating objective event, keeps conversation/message and proposal-revision provenance, checks for an already-active exchange, and admits the request through the durable exchange. An absent origin, unregistered provider, missing exact grant, or authority lookup failure leaves the objective durable and records a recoverable reasoning failure. The active office principal is resolved from the authorized `AuthorityRegistry` snapshot and rechecked during exact `resident.reasoning.escalate` checks for `provider:<id>` using the resident credential. No office-name-to-principal shortcut is used. These source changes are covered by disposable PostgreSQL integration; production provider mapping, grant, migration state, and service deployment remain unverified.

For multi-step proposals, migration `0009_durable_objective_steps.sql` stores stable step order, dependencies, status and assignment identity. The service dispatches only dependency-ready steps; dependent steps wait for independently accepted verification. Conversation-origin objectives remain open until every step is verified and Grace records `OBJECTIVE_COMPLETE` for the matching completion cycle. A structured post-verification review can append a bounded continuation to the same objective; it cannot expand the original acceptance envelope, bypass the current office binding, or create authority. Continuation steps return through ordinary assignment.create validation, leased execution, independent verification, and the cycle-keyed conversation-result outbox. Outbox receipts are unique per completion cycle so earlier verified work can be returned even as the same objective continues. A persisted verified-result review can be reconsidered only through a new evidence-revision event with the exact objective-scoped `objective.submit` grant. The ledger bounds reviews to four generations per completion cycle and stores each request's evidence revision, digest, actor, and idempotency key append-only. Generation-specific conversation response IDs keep prior decisions and receipts intact and make retries idempotent within a generation. Requesting a review never proposes or dispatches s2; any later exact-step continuation and `assignment.create` check remains independent.

Comms5 stale-base revalidation preserves the failed assignment as blocked and unaccepted. It requires fresh VERIFIED repository grounding and appends a same-scope successor assignment step. Direct dependent steps are retargeted to the successor and remain gated by Grace review after independent verification. Objective completion treats the predecessor failure as resolved only when the linked revalidation successor is verified; a failed/rejected worker result is never promoted to success. Resource-policy migration `0012_resource_selection_policy.sql` is required before policy status/mutation or scheduler enforcement is available; an absent table is not treated as an empty policy in a release that includes these operations.

The Comms5-only packager, `scripts/package_comms5_camrui.py`, remains scoped to that service. Changes spanning the Grace runner, resident reasoning, durable exchange, or scheduler policy use the immutable full-source package from `scripts/build_camrui_package.py`; its package is built from one committed revision and includes tracked source and migrations. Install the relevant Grace and Comms5 release pointers independently with their own predecessor and rollback records. The package regression test requires both migrations `0011` and `0012` and all runtime initiation/consumption components in the full package. A passing package check proves artifact contents and integrity only; it does not apply migrations or commission service grants.

The owner-session process uses the existing restricted `riverview_core` PostgreSQL role. Migration `0007_grace_runtime_objective_and_health_acl` grants only the selected columns used by the existing pipeline: read/insert/update columns on `grace_objectives`, read/insert columns and sequence usage on `grace_objective_events`, and heartbeat insert/update columns on `grace_execution_health`. Migration `0009_durable_objective_steps.sql` is the additive per-step persistence prerequisite for multi-step plans; it does not authorize the service to modify any unrelated relation. Existing read-only health migration remains separately scoped. Missing grants produce a sanitized `InsufficientPrivilege` failure; do not work around them with schema-wide privileges.

For a router-bound Grace, `configured_resident_providers()` constructs the same provider set for ResidentReasoner and the result-return conversation service. It verifies the live binding revision, explicit private-LAN router opt-in, configured model digests and allowlisted endpoint/model identities. Typed proposals require `grace.reasoning.80b`; the router does not substitute smaller models. Provider, served model, digest and stage are persisted with the proposal.

After a final step has independent `ACCEPTED` verification, the service first persists `execution.step_verified` and leaves the conversation-origin objective open while `pending_conversation_results()` selects that cycle. The service rechecks the current resident binding and exact `resident.conversation.send` grant, provides the digest-verified artifact and verifier evidence to Grace's bounded 80B review, and inserts a deterministic assistant response in the source conversation. The durable review decision is part of the receipt. Only `OBJECTIVE_COMPLETE` permits the subsequent completion reconciler to append `objective.completed`; other decisions retain the open state. The pending outbox's numeric `completion_cycle` is authoritative for the durable acknowledgement; publisher receipts may omit this field. If a publisher includes it, a mismatched value is rejected. A successful insert followed by acknowledgement records one cycle-specific event, so the next service poll no longer retries that result. If insertion succeeds but acknowledgement fails, retry finds the response receipt without another model call or assistant event. Failures before insertion leave the outbox eligible for retry. This is source implementation only; this increment applies no migrations and provisions no service credentials or grants.
After independent `ACCEPTED` verification, `pending_conversation_results()` selects a conversation-origin result when its initial review is unpublished or when an append-only, authorized re-review generation is pending. The service rechecks the current resident binding and exact `resident.conversation.send` grant, performs a bounded 80B review of verified completion evidence plus the authorized evidence revision, and inserts a deterministic generation-specific assistant response in the source conversation. After insertion but before objective-event acknowledgment, retry reads the persisted response and decision receipt without another model call or assistant event, then appends the missing acknowledgment. Earlier generations remain immutable; failures before insertion leave the durable request eligible for retry. This is source implementation only; no production control endpoint or service release is commissioned by this increment.

In each `GraceExecutionService.run_once()` cycle, ready proposal dispatch, leased worker work, verification, completion reconciliation, result publication, and already-durable proposal review run before grounded-objective or external reasoning calls that may wait on a model/provider. The existing fair objective selector and owner-session cycle remain authoritative; no second queue is introduced. This prevents an unrelated slow proposal-generation call from delaying already-authorized ready work while retaining the selector's bounded fairness for pending grounded objectives.

### Lifecycle criteria, engineering deliverables, and semantic acceptance

The original objective's acceptance criteria are preserved exactly. `PlanProposal.system_owned_criteria` identifies only criteria satisfied by durable system lifecycle evidence, such as conversation result publication or a same-cycle Grace completion decision. Those criteria do not generate Engineering assignments. Remaining criteria are assigned to proposal steps and must exactly cover the objective's deliverable criteria. A sufficient single deliverable can therefore use one assignment; genuinely separate or dependent engineering deliverables remain multi-step.

Independent artifact verification continues to enforce integrity, provenance, scope, and mandatory structure. JSON syntax or a successful-looking envelope is not enough: an authoritative negative outcome such as `REJECTED`, `FAILED`, or `BLOCKED` is rejected, and explicit literal/path criteria are checked against substantive artifact content rather than echoed acceptance metadata. Grace evaluates substantive acceptance criteria using the verified artifact and verifier evidence. A verifier rejection remains durable evidence for Grace's decision; it does not automatically trigger Codex rework or become success.

Regression coverage for these changes runs against disposable fixtures. The production smoke-test objective and production database are not modified by this source increment.

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

The default runner sets three persisted dispatch failures, three persisted retry-safe lease recoveries, and three persisted verifier invocation failures per attempt before leaving work for operator review. Retry exhaustion and verifier failures remain visible in objective projections. The execution retry ceiling is enforced by the worker recovery coordinator and its `retry_exhausted` record; no retry count is stored only in process memory. Verifier failures are isolated per candidate, so one malformed result cannot starve other assignments in a poll. Conversation result publication retries from objective state and uses a deterministic response ID. Side effects of this bounded artifact action are idempotent by assignment and content. Other capabilities must supply their own effect classification and recovery contract. Cancellation uses the pre-execution exact-grant pipeline path. A running action is never force-cancelled.

## Runtime configuration and commissioning boundary

`deploy/systemd/riverview-grace-execution.service` is the isolated service-identity template. `deploy/systemd/riverview-grace-execution-owner-session.service` is an explicit subscription-auth mode running as the existing `admin1` owner. Writable Codex runtime state is under the service's private state directory; the runner resolves `RIVERVIEW_CODEX_HOME` explicitly under that directory, separate from `HOME`. Only `/home/admin1/.codex/auth.json` is bind-mounted read-only into the service-local `codex-home`; credentials are not copied. The bind target directory is owned by `admin1` mode `0700`, and its empty target file is mode `0600`; the systemd mount overlays the existing protected owner file within the service namespace. The runner must not derive CODEX_HOME from HOME. No `OPENAI_API_KEY` is used. The Codex executable must be installed at the root-managed `/opt/riverview-codex/bin/codex` path, outside the personal home. The integrated executable package must also contain its executable `codex-code-mode-host` companion; service preflight now fails closed if it is absent. Riverview's dispatch, executor, verifier and resident credentials are separately injected through protected systemd credentials, and the same exact grants/lease/verification checks remain in force. The CLI is noninteractive after login. A saved login that expires or requires refresh fails closed; an owner must reauthenticate through the existing CLI login. The owner-session unit narrowly permits `AF_INET AF_UNIX AF_NETLINK`; the latter is required by bubblewrap `--unshare-net` loopback setup. Adapter preflight exercises that same network namespace before dispatch and fails closed if it cannot initialize. `MemoryDenyWriteExecute=no` is limited to this owner-session unit because the pinned Code Mode host traps under MDWE; Codex commands remain in `workspace-write` with `sandbox_workspace_write.network_access=false`, the AppArmor-confined bubblewrap sandbox, and the unit filesystem/address-family restrictions. No unsandboxed execution mode is used.

Both units expect an immutable `/opt/riverview-grace-execution/current` release and the existing `/opt/riverview-core/.venv` Python environment. They require protected systemd credentials named `pgpass`, `dispatch-token`, `worker-token`, `verifier-token`, `resident-token`, and `dashboard-token` (the same dashboard read credential used by Comms5), plus root-owned `/etc/riverview/grace-execution.env` containing office ID, non-secret executor/verifier IDs, exact scope, pinned repository commit, and approved model endpoint/digest settings. Authority migrations 0000–0003 and the existing function-only runtime boundary must be present. `AuthorityRegistry(runtime_safe=True)` rechecks the bound office and `office.state.write` grant. Required migrations are applied only through the controlled deployment procedure; the service never applies DDL automatically. Migration `0007_grace_runtime_objective_and_health_acl` is required for the existing objective pipeline and heartbeat; migration 0008 and the resident Level 4 profile are not dependencies. Neither unit is installed or activated by this source change.

Read-only diagnosis:

```sh
systemctl show riverview-grace-execution.service -p ActiveState -p SubState -p MainPID
journalctl -u riverview-grace-execution.service --since=-15m --no-pager
psql "$RIVERVIEW_READONLY_DSN" -X -v ON_ERROR_STOP=1 -c "SELECT service_id,status,last_heartbeat_at,last_cycle_at,last_error_type,cycles_completed FROM riverview_dev.grace_execution_health"
```

Expected service status is `healthy`, with `last_heartbeat_at` newer than the dashboard stale threshold. A missing/stale row is not healthy. `last_error_type` contains only a class name. On service failure, inspect the journal and health row, verify unit credential ownership/permissions and exact grants without printing token contents, correct the underlying configuration, then use the authorized systemd restart procedure. Never delete objective, assignment, attempt, event, or verification rows to recover. Resume is automatic from durable state after the service starts.

## Verification and limitations

The integration tests use isolated PostgreSQL schemas, a temporary Git repository, local HTTP server, deterministic typed proposal, existing bounded worker, and a separate verifier identity. The new owner-session tests use only a synthetic auth-file marker, prove TTY-free construction under the owning identity, and reject weak/copy auth files. A real bounded adapter call reached the existing ChatGPT CLI but did not create a file; the local bwrap/unshare probe failure is reproduced and now blocks adapter preflight. The full PostgreSQL suite passed on a disposable PostgreSQL 16 cluster with the restricted-role fixture; teardown left no test schemas and the cluster shut down cleanly. This service is not live-commissioned; no real Grace website work order, independently accepted Codex artifact, or continuous service run is claimed.

Canonical graph: `process_graphs/grace/operational-integration.json`. Generated views are updated with `python3 scripts/process_graph.py generate`; validate with `python3 scripts/process_graph.py check` and `python3 scripts/process_graph.py validate`.

### Concurrent artifact and source-change enrollment

The owner-session runner can host the existing artifact loop and a distinct
source-change loop concurrently. The artifact worker ID, credential, registry
entry and grants remain as provisioned. The source worker uses a different ID,
protected `source-worker-token`, registry capability, PostgreSQL adapter
connection, and exact `worker.register` plus `assignment.execute` grants. Each
loop claims only its own capability. Worker errors are isolated per cycle; the
other loop continues. Independent verification selects its action from the
persisted attempt capability.

Resident grounding remains in `grace_objectives.source_revision` and
`source_sha256`. Every new source-change plan step separately requires an
explicit `repository_reference` and immutable `repository_revision`. At
dispatch, the append-only `work_order.dispatched` event snapshots the target,
commit, authorized paths, test targets, objective, assignment, step, capability
and proposal-step digest. Dispatch requires the target text in the Steward's
request/criteria. The executor then checks that snapshot against the proposal,
configured repository mapping and actual checkout HEAD. Result and verifier
checks retain the same repository identity and commit. Unbound historical
source-change assignments are rejected without editing their records; artifact
plans remain compatible. The event snapshot requires no database migration.

Source execution remains disabled unless an operator installs the optional
`deploy/systemd/riverview-grace-execution-owner-session-source-worker.conf`
drop-in after enrollment. Enrollment requires a newly distinct source worker
credential, active registration, exact source capability, exact
`worker.register`/`assignment.execute` grants in the existing Engineering
scope, configured repository map/HEAD, and bounded
`RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS`. Do not copy the artifact credential or
grant paths beyond the Steward-approved objective. Missing source enrollment
keeps source steps undispatched while artifact execution remains available.
This branch does not provision credentials or grants, install/enable the
drop-in, apply production migrations, or activate the source worker.

Canonical graph: `process_graphs/grace/operational-integration.json`. Generated views are updated with `python3 scripts/process_graph.py generate`; validate with `python3 scripts/process_graph.py check` and `python3 scripts/process_graph.py validate`.

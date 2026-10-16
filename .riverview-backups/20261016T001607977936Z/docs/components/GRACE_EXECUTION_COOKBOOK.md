<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_COOKBOOK.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.1.0
Purpose: Diagnose and safely resume the persistent Grace execution service
Authority: Read-only diagnosis first; exact grants required for every mutation
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add service operations and recovery procedures
Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Document the one-objective ChatGPT-session run and its fail-closed checks
Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Add diagnosis and retry behavior for proposal routing and source-chat result return
Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Document the persistent no-copy ChatGPT owner-session unit and its recovery boundary
Changed: 2026-10-15 UTC | RV-GRACE-CODEX-SANDBOX-READINESS-001 | Document fail-closed sandbox readiness and safe host blocker handling
Changed: 2026-10-15 UTC | RV-GRACE-HEALTH-WRITER-ACL-001 | Diagnose and recover the restricted-role heartbeat privilege failure
Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Record successful bwrap trial, protected credential paths, and reversible owner-session staging
Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RECOVERY-001 | Diagnose durable objective receipts masked by knowledge-root mismatch and retry safely by origin
Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RETRY-003 | Reuse recorded criteria on same-origin retry and distinguish source identity conflicts
Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-REGROUND-001 | Diagnose and resume verified evidence retries from WAITING_FOR_EVIDENCE
Changed: 2026-10-15 UTC | RV-GRACE-GROUNDING-BOUNDED-001 | Diagnose evidence overflow from broad queries and describe ranked bounded retrieval
-->
# Grace Execution Service — Troubleshooting and Recovery

## Read-only health check

Run as an operator with permission to inspect systemd and use a read-only PostgreSQL identity:

```sh
systemctl show riverview-grace-execution.service -p ActiveState -p SubState -p MainPID
journalctl -u riverview-grace-execution.service --since=-15m --no-pager
psql "$RIVERVIEW_READONLY_DSN" -X -v ON_ERROR_STOP=1 -c "SELECT service_id,status,last_heartbeat_at,last_cycle_at,last_error_type,cycles_completed FROM riverview_dev.grace_execution_health"
```

Expected: `ActiveState=active`, `SubState=running`, a recent `last_heartbeat_at`, and `status=healthy`. The observed heartbeat is stale after the configured dashboard threshold; no row means `not_initialized`, not healthy. Logs contain failure classes and durable IDs only, never bearer credentials, objective request bodies, or artifact contents.

## Symptoms and recovery

| Symptom | Likely cause / first check | Safe recovery | Verify / escalation |
| --- | --- | --- | --- |
| Unit exits during startup | Check sanitized `grace_service_configuration_error` or `grace_service_start_failed`; inspect unit environment and migration version. | Correct the exact missing non-secret setting or protected credential file through the authorized provisioning process. Do not edit live DB grants by hand. | Re-read health and journal; escalate missing/ambiguous grants to Steward/authority owner. |
| `grace_heartbeat_write_failed` or `grace_execution_cycle_failed` with `InsufficientPrivilege` | The restricted runtime role lacks the selected objective/event and health columns. Inspect only `has_column_privilege` for required columns and verify migration `0007_grace_runtime_objective_and_health_acl` checksum in `riverview_dev.schema_migrations`; do not read objective or conversation data to diagnose ACLs. | After a protected backup and exact checksum preflight, apply only the reviewed additive resident-execution migration with the standard migration runner, then start/restart only the Grace owner-session unit. It grants selected columns on `grace_objectives`, `grace_objective_events`, the one required event sequence, and `grace_execution_health`. It grants no event update/delete, objective identity update, unrelated table DML, or protected authority access. | Require `_proposed()`/objective projections to return without privilege errors, a fresh healthy heartbeat with `last_error_type IS NULL`, and a working restricted-role dashboard projection. If the relation, role, or checksum differs, stop and retain diagnostics. |
| Objective remains `WAITING_FOR_EVIDENCE` | Read only evidence status, source revision/hash, reference count, retrieval flag and selection-policy metadata. An `INCOMPLETE` result with verified source revision/hash but no selected value can mean relevant passages exceeded the context budget; do not print the objective or conversation body to diagnose it. | Confirm the package-pinned source set is intact. The resident selector verifies the complete allowlisted corpus, then deterministically ranks whole matching paragraphs within a 7 KiB selection budget; full source references and digest remain recorded. If no whole passage fits, leave the objective pending. After a provider correction, retry the same authenticated source message with blank criteria through the origin-idempotent intake route. A VERIFIED retry must atomically persist the evidence and transition the same row from `WAITING_FOR_EVIDENCE` to `GROUNDED`; if it does not, inspect the objective revision and the grounded/waiting events before any repeated retry. | Expect the same objective ID. It may advance only after `VERIFIED` grounding with complete source retrieval. Bounded selection metadata distinguishes full corpus verification from the subset passed to reasoning. Missing or oversized evidence cannot be overridden. |
| Website reports an intake conflict after a retry | Inspect objective status and `objective.received` origin metadata only; do not read the conversation body. A committed objective may exist while grounding waits. Confirm the active dashboard release and served asset identity. | Do not create a replacement objective or edit the ledger. For the same authenticated source, the endpoint revalidates `objective.submit`, preserves the original recorded criteria, and retries grounding; the criteria field may be blank. Retry-entered criteria never rewrite the existing objective. New sources still require criteria. | Expect the same objective ID and a `202` receipt with its current state. `work_order_origin_conflict` denotes a different source binding or ambiguous origin; authorization denial remains 403. A wait receipt is not a proposal, assignment, or approval. |
| Grounded conversation objective has no proposal | Inspect sanitized `resident_reasoning_cycle_failed` events and current office binding/provider identifiers; do not use conversation bodies from logs. | Confirm router digest matches the active binding and approved 80B readiness is `READY`; correct configuration only through the authorized release process. | Persistent service retries; any proposal must carry 80B provider/model provenance. Smaller models cannot propose Engineering work. |
| Objective completed but source conversation has no result | Inspect `objective.completed`, `conversation.result_published`, current Grace binding, and sanitized service failure type. Use the authenticated API for metadata-only conversation inspection. | Restore exact `resident.conversation.send` authorization or 80B readiness through the approved process. Never manually mark the outbox published. | Next service cycle retries. Deterministic response identity prevents a duplicate assistant event after a successful insert. |
| Objective remains `PROPOSED` | Inspect `execution.dispatch_failed` event count and configured exact scope. Three failures stop automatic dispatch. | Correct service identity/scope/grant via governed authority provisioning. Do not manually change objective status. | Service will retry after restart only while below the three-failure cap. At cap, escalate and create a new authorized correction decision before resuming. |
| Assignment is queued | Confirm event processor service, assignment event, scope and worker registry. | Restore the existing event processor; do not manually set `ready` in a live schema. | Wait for its durable queued-to-ready transition, then confirm worker attempt/lease evidence. |
| Assignment is blocked after worker failure | Inspect assignment events, worker attempts, execution intent and CME attention projection. | Let existing lease recovery reconcile only when safe; this worker is classified `retry_safe`. Correct the action fault first. | The artifact action is content-idempotent. Unknown external effects must remain in the existing Steward wait path. |
| Assignment awaits verification | Check successful attempt result and verifier registry/lease/service. | Restore the distinct verifier service identity and exact `assignment.verify` grant. | Only a separately recorded `ACCEPTED` decision permits objective completion. |
| Verification failures reach three | Inspect objective `verification_failures`, the three `execution.verification_failed` events and verifier journal. | Correct verifier/runtime faults; the poller caps retries per attempt and proceeds to other candidates. Do not change the assignment state manually. | The item remains awaiting verification and objective remains incomplete until independent verification succeeds; escalate unresolved evidence integrity concerns. |
| Dashboard says Grace unavailable/stale | Check `/api/v1/status`, dashboard journal, migration presence and heartbeat age. | Restore dashboard/database connectivity; do not infer health from systemd active state alone. | Confirm the service instance, fresh heartbeat, objective detail, artifact digest and verification decision. |
| Process restart during work | Inspect the latest lease generation, execution intent, attempt/result and recovery record. | Start the supervised service; it reads PostgreSQL and CME reconciles expired leases. Do not replay a completion manually. | A preserved result proceeds to verification; a safe action may be requeued; uncertain effects stay blocked for Steward. |
| Codex capability reports unavailable before assignment | Check sanitized `codex_sandbox_unavailable`; run the bwrap probe and inspect the loaded per-executable AppArmor policy without changing the global namespace restriction. | Keep the objective durable and un-dispatched. Do not select a danger-full-access mode. The authorized `/usr/bin/bwrap` profile trial passed; direct `unshare` remains restricted by design. | Repeat `bwrap --ro-bind / / --proc /proc --dev /dev /bin/true` from the owner-session context. If it fails, preserve the request and follow the sandbox rollback record in the commissioning guide. |

## One-objective supervised Codex run

The supported subscription path is an interactive `admin1` invocation. It does
not copy `~/.codex` into the Riverview service account and never supplies an
`OPENAI_API_KEY`. The transient systemd unit exposes the existing Codex home
read-only, loads only the pre-provisioned Riverview runtime credentials, and
writes workspaces/artifacts under the private `~/.local/share/riverview-grace`
directory. The runner accepts one objective ID, displays Grace's persisted
proposal, requires the operator to type `EXECUTE <objective-id>`, and exits
after one assignment-specific dispatch/claim/verification cycle.

```sh
scripts/run_supervised_grace_execution.sh objective:<persisted-id>
```

This command is commissioning-ready source, not an indication that the
transient unit can currently start. It requires the installed release under
`/opt/riverview-grace-execution/current`, the approved environment file, all
five protected credential files, registered executor/verifier identities and
active exact grants. It also refuses to reason unless the configured resident
provider model identity contains `80b`. A missing resource/credential or failed
exact grant leaves the assignment incomplete; do not create a local substitute
artifact or replay the command without checking the durable assignment state.

The selected objective remains tied to the existing `grace.objective-work-order.v1`
workflow. Targeted claim skips global expired-lease reconciliation so this
supervised invocation cannot mutate unrelated assignments. Resume broader
recovery through the persistent CME service only.

## Persistent ChatGPT owner-session service

For automatic progression after website intake, the explicit
`riverview-grace-execution-owner-session.service` template runs continuously as
`admin1` and uses the existing `~/.codex` login in place. `ProtectHome=tmpfs`
and `BindReadOnlyPaths=/home/admin1/.codex` expose only that read-only path; no
Codex login file is copied into the `riverview` identity. The five Riverview
credentials are separate, exact-unit `LoadCredential` inputs. The owner-session
unit is opt-in and does not install itself or alter live authority.

Read-only diagnostics:

```sh
systemctl show riverview-grace-execution-owner-session.service -p ActiveState -p SubState -p MainPID
journalctl -u riverview-grace-execution-owner-session.service --since=-15m --no-pager
sudo -u postgres psql -X -d riverview -c "SELECT service_id,status,last_heartbeat_at,last_cycle_at,last_error_type FROM riverview_dev.grace_execution_health WHERE service_id='grace.execution.v1'"
```

Expected: active unit, recent healthy heartbeat, and separately registered
executor/verifier capabilities in the `work-order:engineering` scope. If the
saved ChatGPT login expires, a Codex child failure leaves the assignment
durable and incomplete. Authenticate again as `admin1` using the existing
interactive Codex login procedure, then allow the current service's normal
lease/recovery cycle to resume it. Do not replay or create another objective.
No `OPENAI_API_KEY`, `CODEX_ACCESS_TOKEN`, or credential copy is part of this
mode. A machine that requires unattended credential refresh should use a
separately authorized supported workspace-token arrangement, not bypass this
owner-session boundary.

## Owner-session provisioning status (2026-10-15)

The authorized fixed grant set and dedicated dispatch, executor, and verifier credentials are provisioned through the root-local `scripts/provision_grace_engineering_demo.py --apply` procedure. It reuses active exact grants and fails on principal-kind, grant-ID, or revoked-grant conflicts. Credential contents are never printed. The resident token loads from `/etc/riverview/grace/resident.credential`; no resident token copy is made.

The owner-session unit and environment installer remains unrun until the reviewed immutable execution package is staged. `scripts/install_grace_owner_session.py --check` validates the immutable source and unit without changing the host. `--apply` stages only the owner-session unit and non-secret environment, then daemon-reloads systemd; it does not enable or start the service. Save the two returned SHA-256 values. Roll back with `scripts/install_grace_owner_session.py --rollback <UNIT_SHA256> <ENV_SHA256>`; both hashes are validated before either file is removed. This procedure does not touch the dashboard.

The per-executable AppArmor profile trial is active and the global user-namespace restriction remains enabled. One bounded Codex CLI task created a real Markdown artifact in a disposable workspace. This does not prove persistent worker dispatch or independent verification.

## Destructive-operation warning

Never delete or reset the schema, objective/event rows, assignment ledger, leases, attempts, worker results, verification records, artifact workspace, or credentials as a recovery shortcut. Preserve the relevant DB backup and evidence before any separately authorized migration rollback or data repair. This work order did not authorize live commissioning or production changes.

<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_COOKBOOK.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.2
Purpose: Diagnose and safely resume the persistent Grace execution service
Authority: Read-only diagnosis first; exact grants required for every mutation
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add service operations and recovery procedures
Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Document the one-objective ChatGPT-session run and its fail-closed checks
Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Add diagnosis and retry behavior for proposal routing and source-chat result return
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
| Objective remains `WAITING_FOR_EVIDENCE` | Read objective evidence status, source commit and references through the authenticated dashboard. | Restore the pinned repository package or knowledge provider; resubmission is not necessary. | It may advance only after complete `VERIFIED` grounding. Missing knowledge cannot be overridden. |
| Grounded conversation objective has no proposal | Inspect sanitized `resident_reasoning_cycle_failed` events and current office binding/provider identifiers; do not use conversation bodies from logs. | Confirm router digest matches the active binding and approved 80B readiness is `READY`; correct configuration only through the authorized release process. | Persistent service retries; any proposal must carry 80B provider/model provenance. Smaller models cannot propose Engineering work. |
| Objective completed but source conversation has no result | Inspect `objective.completed`, `conversation.result_published`, current Grace binding, and sanitized service failure type. Use the authenticated API for metadata-only conversation inspection. | Restore exact `resident.conversation.send` authorization or 80B readiness through the approved process. Never manually mark the outbox published. | Next service cycle retries. Deterministic response identity prevents a duplicate assistant event after a successful insert. |
| Objective remains `PROPOSED` | Inspect `execution.dispatch_failed` event count and configured exact scope. Three failures stop automatic dispatch. | Correct service identity/scope/grant via governed authority provisioning. Do not manually change objective status. | Service will retry after restart only while below the three-failure cap. At cap, escalate and create a new authorized correction decision before resuming. |
| Assignment is queued | Confirm event processor service, assignment event, scope and worker registry. | Restore the existing event processor; do not manually set `ready` in a live schema. | Wait for its durable queued-to-ready transition, then confirm worker attempt/lease evidence. |
| Assignment is blocked after worker failure | Inspect assignment events, worker attempts, execution intent and CME attention projection. | Let existing lease recovery reconcile only when safe; this worker is classified `retry_safe`. Correct the action fault first. | The artifact action is content-idempotent. Unknown external effects must remain in the existing Steward wait path. |
| Assignment awaits verification | Check successful attempt result and verifier registry/lease/service. | Restore the distinct verifier service identity and exact `assignment.verify` grant. | Only a separately recorded `ACCEPTED` decision permits objective completion. |
| Verification failures reach three | Inspect objective `verification_failures`, the three `execution.verification_failed` events and verifier journal. | Correct verifier/runtime faults; the poller caps retries per attempt and proceeds to other candidates. Do not change the assignment state manually. | The item remains awaiting verification and objective remains incomplete until independent verification succeeds; escalate unresolved evidence integrity concerns. |
| Dashboard says Grace unavailable/stale | Check `/api/v1/status`, dashboard journal, migration presence and heartbeat age. | Restore dashboard/database connectivity; do not infer health from systemd active state alone. | Confirm the service instance, fresh heartbeat, objective detail, artifact digest and verification decision. |
| Process restart during work | Inspect the latest lease generation, execution intent, attempt/result and recovery record. | Start the supervised service; it reads PostgreSQL and CME reconciles expired leases. Do not replay a completion manually. | A preserved result proceeds to verification; a safe action may be requeued; uncertain effects stay blocked for Steward. |

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

## Destructive-operation warning

Never delete or reset the schema, objective/event rows, assignment ledger, leases, attempts, worker results, verification records, artifact workspace, or credentials as a recovery shortcut. Preserve the relevant DB backup and evidence before any separately authorized migration rollback or data repair. This work order did not authorize live commissioning or production changes.

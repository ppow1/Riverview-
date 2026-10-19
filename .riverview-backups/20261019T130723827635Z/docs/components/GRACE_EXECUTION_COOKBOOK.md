<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_COOKBOOK.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.1.14
Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Document source-worker enrollment, diagnostics, and reversible disablement.
Purpose: Diagnose and safely resume the persistent Grace execution service
Authority: Read-only diagnosis first; exact grants required for every mutation
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add service operations and recovery procedures
Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Document the one-objective ChatGPT-session run and its fail-closed checks
Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Add diagnosis and retry behavior for proposal routing and source-chat result return
Changed: 2026-10-16 UTC | RV-GRACE-RESULT-RETURN-DIAGNOSTICS-001 | Document sanitized provider-attempt evidence for deferred review retries
Changed: 2026-10-16 UTC | RV-GRACE-RESULT-RETURN-DIAGNOSTICS-001 | Set and document the bounded 512-token structured-review default after live adapter reproduction
Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Document the persistent no-copy ChatGPT owner-session unit and its recovery boundary
Changed: 2026-10-15 UTC | RV-GRACE-CODEX-SANDBOX-READINESS-001 | Document fail-closed sandbox readiness and safe host blocker handling
Changed: 2026-10-15 UTC | RV-GRACE-HEALTH-WRITER-ACL-001 | Diagnose and recover the restricted-role heartbeat privilege failure
Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Record successful bwrap trial, protected credential paths, and reversible owner-session staging
Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RECOVERY-001 | Diagnose durable objective receipts masked by knowledge-root mismatch and retry safely by origin
Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RETRY-003 | Reuse recorded criteria on same-origin retry and distinguish source identity conflicts
Changed: 2026-10-15 UTC | RV-GRACE-OBJECTIVE-REGROUND-001 | Diagnose and resume verified evidence retries from WAITING_FOR_EVIDENCE
Changed: 2026-10-15 UTC | RV-GRACE-GROUNDING-BOUNDED-001 | Diagnose evidence overflow from broad queries and describe ranked bounded retrieval
Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Diagnose durable dependency-step dispatch and isolated source-change patch verification
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-OWNER-STATE-001 | Diagnose owner-session initialization without exposing credentials and distinguish missing Code Mode package files
Changed: 2026-10-16 UTC | RV-GRACE-RECOVERY-HOOK-001 | Diagnose stale startup recovery hook names and preserve the same assignment's no-artifact retry boundary
Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Diagnose immutable objective versus current grounding revision mismatch and bounded no-launch recovery
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-BOUNDED-RETRY-001 | Diagnose committed single-file output rejection and recover typed no-artifact failures within the existing retry ceiling
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-SYSTEMD-NETLINK-001 | Diagnose bwrap NETLINK_ROUTE failure under owner-session address-family restrictions and validate exact sandbox setup in preflight
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-ENABLE-001 | Enable Codex code_mode_host explicitly when subscription-authenticated owner-session execution requires real file operations
Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-MDWE-001 | Diagnose Code Mode host SIGTRAP under MDWE and document owner-unit-scoped remediation with retained sandbox controls
Changed: 2026-10-16 UTC | RV-GRACE-OWNER-CODEX-HOME-001 | Diagnose owner-session startup when HOME differs from explicit CODEX_HOME and require a private bind target
Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Diagnose preserved verifier rejection, revision recheck, and interruption-safe completion
Changed: 2026-10-17 UTC | RV-GRACE-ACCEPTANCE-CRITERIA-001 | Diagnose criteria result-echo gaps using the authoritative persisted objective step
Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Diagnose latest rejection selection, same-assignment lease fencing and persistent conversation progress
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
| Objective completed but source conversation has no result | Inspect `objective.completed`, `conversation.result_published`, current Grace binding, and the `grace_result_review_deferred` event for readiness state, provider, model, elapsed time, bounded error code, finish reason, and completion-token limit. These fields contain no request/response text. Use the authenticated API for metadata-only conversation inspection. | The structured review uses `RIVERVIEW_GRACE_RESULT_REVIEW_TOKENS` (default 512, allowed 16–512). If diagnostics show `response_incomplete` with `finish_reason=length`, confirm the effective limit and correct it within that range; never accept a truncated response or manually mark the outbox published. | Next service cycle retries. Deterministic response identity prevents a duplicate assistant event after a successful insert. |
| Objective remains `PROPOSED` | Inspect `execution.dispatch_failed` event count and configured exact scope. Three failures stop automatic dispatch. | Correct service identity/scope/grant via governed authority provisioning. Do not manually change objective status. | Service will retry after restart only while below the three-failure cap. At cap, escalate and create a new authorized correction decision before resuming. |
| Assignment is queued | Confirm event processor service, assignment event, scope and worker registry. | Restore the existing event processor; do not manually set `ready` in a live schema. | Wait for its durable queued-to-ready transition, then confirm worker attempt/lease evidence. |
| Assignment is blocked after worker failure | Inspect assignment events, worker attempts, execution intent and CME attention projection. | Let existing lease recovery reconcile only when safe; this worker is classified `retry_safe`. Correct the action fault first. | The artifact action is content-idempotent. Unknown external effects must remain in the existing Steward wait path. |
| Codex reports `workspace_change_set_invalid` with no attempt or artifact | Inspect only the assignment's execution-intent failure class, attempt/result/verifier counts and assignment-bound artifact metadata. Codex CLI output and conversation bodies are not required. | The legacy artifact capability accepts only `deliverable.md`. Source changes require the separate `engineering.codex-cli-source-change.v1` capability, an explicit assignment path allowlist, an immutable base revision, patch digest/inventory, and passing fixed tests. | A typed `CodexActionFailure` can resume after lease expiry only when the objective provenance remains verified, no attempt/result/verifier/artifact exists, and the existing retry ceiling permits it. Recovery records the decision and normal claim-time exact grant validation runs again. Any existing artifact or generic unknown exception remains blocked for Steward review. |
| A dependent Engineering step is not dispatched | Inspect `grace_objective_steps` status, assigned work-order ID, `depends_on`, and verifier decision for each predecessor. Do not dispatch by editing assignment state. | Only pending steps whose every dependency is independently `verified` are dispatchable. The durable objective-step assignment link resolves task content; the runtime workflow node may change during CME transitions. | Repair the original predecessor through normal lease/recovery and independent verification. The next service poll claims the next dependency-ready step. |
| Codex verifier reports `acceptance_criteria_are_present=false` | Read the objective's immutable criteria and proposal step, then inspect the `grace_objective_steps` row linked to the assignment. Compare these pre-dispatch records with the worker result's optional criteria echo. Do not edit criteria or verifier records after execution. | The Codex verifier resolves expected criteria by objective and assignment IDs from the durable objective step. A missing or empty step/link remains rejected; an omitted result echo does not erase criteria persisted before dispatch. | If intake/proposal/step criteria were missing before dispatch, preserve the rejected attempt and submit a new authorized objective. If only the result echo was absent, deploy the resolver fix and reverify the same immutable artifact through the existing verifier path. |
| Owner-session startup reports `grace_service_start_failed` with `AttributeError` before its healthy event | Confirm the active immutable source commit and compare the service's startup recovery hook with `CodexWorkAction.reconcile_retryable_no_artifact_failures`. Do not inspect objective or conversation bodies. | Deploy a reviewed immutable release whose service entry point calls `reconcile_codex_startup_recovery`; missing hooks now produce the bounded `codex_recovery_hook_unavailable` configuration error. Preserve the existing objective, lease, event history, and release predecessor. | Restart only the owner-session service after package and backup checks. The normal cycle may retry the same assignment only after its lease expires and the recovery coordinator proves verified objective provenance and absence of attempts, results, verifier decisions, and artifact. |
| Assignment awaits verification | Check successful attempt result and verifier registry/lease/service. | Restore the distinct verifier service identity and exact `assignment.verify` grant. | Only a separately recorded `ACCEPTED` decision permits objective completion. |
| Verification failures reach three | Inspect objective `verification_failures`, the three `execution.verification_failed` events and verifier journal. | Correct verifier/runtime faults; the poller caps retries per attempt and proceeds to other candidates. Do not change the assignment state manually. | The item remains awaiting verification and objective remains incomplete until independent verification succeeds; escalate unresolved evidence integrity concerns. |
| Dashboard says Grace unavailable/stale | Check `/api/v1/status`, dashboard journal, migration presence and heartbeat age. | Restore dashboard/database connectivity; do not infer health from systemd active state alone. | Confirm the service instance, fresh heartbeat, objective detail, artifact digest and verification decision. |
| Process restart during work | Inspect the latest lease generation, execution intent, attempt/result and recovery record. | Start the supervised service; it reads PostgreSQL and CME reconciles expired leases. Do not replay a completion manually. | A preserved result proceeds to verification; a safe action may be requeued; uncertain effects stay blocked for Steward. |
| Codex capability reports unavailable before assignment | Check sanitized `codex_sandbox_unavailable`; run the bwrap probe and inspect the loaded per-executable AppArmor policy without changing the global namespace restriction. | Keep the objective durable and un-dispatched. Do not select a danger-full-access mode. The authorized `/usr/bin/bwrap` profile trial passed; direct `unshare` remains restricted by design. | Repeat `bwrap --unshare-net --ro-bind / / --proc /proc --dev /dev /bin/true` from the owner-session context. The owner-session unit must permit only `AF_INET AF_UNIX AF_NETLINK`; bubblewrap uses NETLINK_ROUTE to configure its isolated loopback device. If it fails, preserve the request and follow the sandbox rollback record in the commissioning guide. |
| Owner-session startup reports sanitized `ValueError` or authentication initialization fails before assignment | Inspect only sanitized failure classes, the explicit `RIVERVIEW_CODEX_HOME` path, its owner/mode, and the single-file systemd bind declaration. `HOME` is the service state root and must not be used to infer `CODEX_HOME`; never display auth contents or the full process environment. | Resolve `CODEX_HOME` from `RIVERVIEW_CODEX_HOME` under private service state. Pre-create its directory as `admin1:admin1` mode `0700` and an empty `auth.json` mount target as `admin1:admin1` mode `0600`; the read-only bind alone supplies the existing owner auth file in the service namespace. Do not copy or refresh the login. | Confirm the target is empty before staging, preserve its metadata predecessor, and verify the unit's single-file read-only bind and `ProtectHome=tmpfs`. Run the bounded adapter preflight in owner-session context. If the home escapes state or the mounted auth file is absent/writable, fail closed without consuming a retry. |
| Owner-session Codex preflight returns `codex_code_mode_host_missing` | Inspect the sanitized preflight code and executable package inventory. Never display auth contents or CLI environment. | Keep work pending. Install the reviewed Codex CLI package including executable `codex-code-mode-host`; when required, invoke the CLI with `--enable code_mode_host`. A zero exit without the authorized workspace change remains rejected. Do not copy or refresh the personal login from the service. | Validate the unit with `systemd-analyze verify` and run the bounded adapter preflight as the owner. If the companion binary or valid existing login is unavailable, record the exact readiness failure and do not consume another assignment retry. |
| Code Mode CLI exits but no artifact is produced and kernel journal records `codex-code-mode-host` SIGTRAP | Preserve the assignment; inspect only executable/PID trap metadata and sanitized provider event types. Do not read prompts or authentication files. | The pinned Code Mode host traps under `MemoryDenyWriteExecute=yes`; set `MemoryDenyWriteExecute=no` only on the owner-session unit. Keep bubblewrap workspace-write isolation, disabled network, AppArmor confinement, and systemd filesystem/address-family controls enabled. | Verify through a transient unit matching the owner service that the CLI changes only `deliverable.md`; independently validate the adapter result. Restore MDWE=yes only if Code Mode execution is intentionally disabled, leaving Engineering work blocked rather than consuming retries. |
| Multi-step objective has no dispatchable assignment | Inspect durable step order, dependency identities, prior assignment links, and independent verifier decisions. Do not infer readiness from the objective's latest assignment pointer alone. | Only a step whose earlier dependencies are all independently verified can dispatch. Restore normal CME polling and lease recovery; do not manually create an assignment or mark a step verified. | Verify one stable assignment per step and that retries/restarts do not create duplicate step identities. A failed step remains recoverable or blocked according to its durable retry state. |
| Grace review proposes a continuation after a verified step | Inspect the typed review outcome, objective/cycle IDs, original acceptance envelope, current binding revision, and continuation persistence receipt. Do not interpret model rationale as authority. | Accept only a bounded proposed step inside the original objective and criteria. The ordinary existing assignment.create grant is rechecked by CME; a broader action becomes a Steward-authorization outcome. | Confirm next step uses the same objective and conversation, a distinct stable step/assignment ID, and the cycle-keyed idempotent result outbox. |
| Existing objective is rejected during Codex work-order provenance checks after a release update | Compare the objective row's immutable `source_revision` and `source_sha256` with the same fields in its verified evidence; compare current grounding metadata separately. Do not compare the objective source pin to the current worker-contract release. | Correct the provenance comparison in the Codex action. The objective's original evidence stays unchanged; current contract grounding may legitimately come from a later integrated release. | If a no-launch intent is durably marked failed and the assignment is blocked at `WORKER_PRE_EXECUTION_FAILED`, let the bounded startup recovery run only after its lease expires and it proves no attempt, verifier record, or artifact exists. Normal exact-grant claim validation still applies. |
| `grace_verifier_revalidation_failed` or a rejected Codex artifact after a verifier correction | Read only assignment state, attempt identity/status, verifier revisions and decisions, migration checksum, and exact verifier-grant status. Confirm the release's registered verifier revision. Do not read conversation content or rewrite the original verification row. | If migration `0006_verifier_revision_rechecks` is missing, first take and verify the standard protected backup, then apply only that checksum-pinned worker-adapter migration. The persistent service reopens the same immutable worker result under the newer verifier revision; it never reruns Codex. An accepted row whose state transition was interrupted is completed idempotently on a later cycle using the same revision key. | Expect the original REJECTED row unchanged, at most one additional row for this attempt/revision, the exact current verifier grant revalidated, and assignment completion only after ACCEPTED evidence. If either revision is equal, grant is revoked, migration checksum differs, artifact check fails, or state/attempt identity differs, leave the assignment pending/rework-required and retain sanitized diagnostics. |

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
`admin1` and uses the existing ChatGPT login in place. `HOME` and writable
`CODEX_HOME` are separate: the runner reads `RIVERVIEW_CODEX_HOME` under its
private state root and never derives it from `HOME`. The service-local
`codex-home` directory must be owned by `admin1` mode `0700`; its empty
`auth.json` bind target must be owned by `admin1` mode `0600`. Systemd then
binds only `/home/admin1/.codex/auth.json` read-only to that target while
`ProtectHome=tmpfs` hides the owner home. No Codex login file is copied. The five Riverview
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

## Optional source-change worker commissioning checklist

Source-change execution is source-only in this increment. Do not apply the
optional systemd drop-in or provision credentials/grants without a separate
Steward commissioning approval.

Before enrollment, review the approved repository mapping, exact immutable
target commit, bounded file ceiling and fixed offline test runner. Confirm the
Steward-approved objective itself names the target repository, commit and every
authorized path. The resident grounding `source_revision` is knowledge
provenance and must never be reused as the source target commit.

For an approved commissioning window:

1. Enroll a distinct source worker principal and protected credential through
   the existing authority/worker registration procedure. Do not change the
   artifact principal, token, registry row or grants. Keep the credential in
   `/etc/riverview/worker/grace-source-change.credential`, root-controlled and
   readable only through the matching systemd credential binding.
2. Grant only `worker.register` and `assignment.execute` to that source identity
   in the existing `work-order:engineering` scope. Keep the existing independent
   verifier identity and exact `assignment.verify` grant. Confirm source and
   artifact worker IDs and credential digests are distinct without printing
   credential contents.
3. Configure the exact repository reference, checkout path and approved
   `RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS` JSON list. Check that the checkout HEAD
   equals the approved objective target commit. Do not use a branch name or
   resident grounding revision as the commit pin.
4. Stage the source worker drop-in as
   `/etc/systemd/system/riverview-grace-execution-owner-session.service.d/20-source-worker.conf`
   only after its identity, credential file and grants exist. Validate the
   combined unit with `systemd-analyze verify`; the base unit remains
   artifact-compatible with `RIVERVIEW_SOURCE_WORKER_ENABLED=0`.
5. In the approved window, apply the controlled config backup/release procedure
   and restart only `riverview-grace-execution-owner-session.service`. Confirm
   healthy Grace heartbeat, separate registered capability identities,
   source worker polling, CME assignment state, independent verification, and
   durable result/reconciliation events. Use only a bounded disposable target.

If source startup is incomplete, inspect only sanitized failure class, source
worker ID, capability registry, grant state, configured path ceiling, and
checkout HEAD. Never print credentials or full process environment. Missing
source token/ID/registration/grant/allowlist disables source execution; artifact
execution remains available. A mismatch leaves source work undispatched rather
than routing it through the artifact loop.

Rollback preserves the artifact worker and all CME state: remove only the
source-worker drop-in, run `systemctl daemon-reload`, and restart the owner
session only within the approved maintenance window. Leave the source worker
registration, credential and durable attempts unchanged until separately
authorized retirement. Verify source steps remain pending, artifact polling
continues, and no assignment, result, or conversation publication was
duplicated. Never replay a dispatched source assignment merely to test the
rollback.

## Rejected work and conversation progress

For a durable objective linked to a website conversation, open Talk with Grace and use the **Engineering progress** panel. It reads the authenticated dashboard projection and survives reload. The panel shows objective and assignment IDs, stage, latest event timestamp, verifier rejection reason, rework attempts/decision, and whether Steward action is recorded as required. A blank/no-objective panel is not evidence that an objective belonging to a different conversation is missing.

For read-only diagnosis when the panel reports blocked or unavailable, inspect identifiers and lifecycle only; do not select request text or conversation bodies:

```sh
sudo -u postgres psql -X -d riverview -v objective_id='objective:<id>' \
  -c "SELECT objective_id,status,assignment_id,updated_at FROM riverview_dev.grace_objectives WHERE objective_id=:'objective_id'"
```

A current independent rejection is retained and reviewed by Grace on the persistent owner-session cycle. A decision of `REWORK_PROPOSED` must remain within the original step criteria and pass the existing exact `assignment.create` grant check. The service fences the completed lease and requeues the same assignment with a new generation; it does not create a second assignment or edit criteria. The next successful attempt must receive a new independent verifier record. If the latest Grace decision is `STEWARD_AUTHORIZATION_REQUIRED`, the objective stays incomplete and the panel marks Steward action required. Never change assignment or objective state manually. If the panel does not refresh, reconnect the authorized conversation and use its Refresh button; the API filter is `GET /api/v1/objectives?conversation_id=<uuid>` and returns no transcript bodies.

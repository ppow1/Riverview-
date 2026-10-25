<!--
Riverview~ Controlled Document
File: docs/components/GRACE_EXECUTION_COOKBOOK.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.1.35
Changed: 2026-10-25 UTC | RV-LOCAL-RELEASE-GATE-20261025 | Record local exact-commit qualification and Grace-only immutable release activation/rollback.
Changed: 2026-10-25 UTC | RV-GRACE-S4-EVIDENCE-RECOVERY-20261025 | Require exact replayed grade and feedback evidence before S4 exception issuance.
Changed: 2026-10-25 UTC | RV-GRACE-S4-EVIDENCE-RECOVERY-20261025 | Add read-only diagnostics and recovery steps for consumed-evaluation replay, bounded evidence handoff, and exhausted-rework CME suppression.
Changed: 2026-10-25 UTC | RV-GRACE-LUNA-CME-JSON-DIAGNOSTICS-20261025 | Document JSON-mode input shape and persisted sanitized Luna HTTP failure fields.
Changed: 2026-10-24 UTC | RV-GRACE-LUNA-SUPERVISORY-RETRY-20261024 | Document observed Luna output limits, same-scope retry bounds, and spend verification
Changed: 2026-10-22 UTC | RV-GRACE-DURABLE-COMPLETION-001-DOC-CORRECTION | Make persisted accepted verification, not conversational output, the objective completion authority.
Changed: 2026-10-22 UTC | RV-GRACE-DURABLE-COMPLETION-001 | Document durable terminal completion recovery and distinguish post-completion conversation feedback.
Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Diagnose scheduler ordering, split lifecycle criteria, and distinguish verifier rejection from Grace acceptance
Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-002 | Diagnose dynamic bounded artifact contracts and verifier outcomes
Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Document assignment-defined artifact diagnosis and bounded recovery
Changed: 2026-10-20 UTC | RV-GRACE-MULTISTEP-PROVENANCE-RECOVERY-001 | Diagnose sibling-step pointer mismatches and document same-assignment no-artifact recovery evidence.
Changed: 2026-10-20 UTC | RV-GRACE-ACCEPTED-STEP-REWORK-001 | Add diagnostics and safe recovery for accepted-step dispatch and bounded durable rejection escalation.
Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Preserve production behavior while integrating the authenticated bounded re-review caller.
Changed: 2026-10-19 UTC | RV-C4-GRACE-ACTIVE-LINE-INTEGRATION-001 | Document cross-objective key collision handling and fair pending-review selection.
Changed: 2026-10-19 UTC | RV-C4-GRACE-RESULT-RETURN-DIAGNOSTICS | Document sanitized response-shape diagnostics for invalid 80B result reviews.
Changed: 2026-10-19 UTC | RV-C4-GRACE-RESULT-RETURN-ARTIFACT-STATUS | Add diagnostic and recovery guidance for the bounded artifact-review availability contract.
Changed: 2026-10-19 UTC | RV-C1-GRACE-RESULT-RECEIPT-001 | Diagnose and safely recover missing or mismatched publisher cycle metadata
Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Diagnose exact-text verifier false negatives, preserve verifier evidence, and route the digest-checked artifact to Grace for substantive acceptance or rework decision.
Changed: 2026-10-19 UTC | RV-GRACE-REREVIEW-OPERATOR-CALLER-001 | Document authenticated rereview request, audit receipt, failures, and safe resume.
Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-GENERATIONS-001 | Diagnose bounded evidence revision generations and recover the durable review outbox safely
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
Changed: 2026-10-20 UTC | RV-GRACE-REASONING-PROPOSAL-RECOVERY-20261020 | Diagnose repeated incomplete resident proposals and resume through the existing persistent reasoning loop
-->
# Grace Execution Service — Troubleshooting and Recovery

## Local qualification and Grace release activation

GitHub remains the repository, PR, and issue record. GitHub Actions is
informational and is not a release prerequisite. Before merge, run the full
locally controlled checkout and applicable PostgreSQL regressions on the exact
PR head, record its full commit/tree SHA, commands, versions, results and logs,
and obtain independent review of that same commit. Keep all existing
acceptance, security, authorization, and deployment checks. The general local
qualification evidence contract is in
[`DEVELOPMENT_LIFECYCLE_STANDARD.md`](../standards/DEVELOPMENT_LIFECYCLE_STANDARD.md).

After merge, build and verify the package from the exact merged commit using
`scripts/build_camrui_package.py` and `scripts/verify_camrui_package.py`. Stage
only a new immutable root-owned release under
`/opt/riverview-grace-execution/releases/<full-commit>`. Before activation,
record the current `readlink -f /opt/riverview-grace-execution/current`, verify
that predecessor directory remains present, and preserve the predecessor
pointer plus candidate archive/checksum in a root-only timestamped backup under
`/var/backups/riverview/`. Do not overwrite a release directory or change the
Dashboard release.

Switch only the Grace `current` symlink atomically to the verified release,
then restart only `riverview-grace-execution-owner-session.service` so its
imported code matches the new pointer. Do not restart the Dashboard, CME, event
processor, model services, or workers for a source-only Grace change. This
change has no database migration; leave all objective and event records alone.
Verify the active release SHA, owner-session health/heartbeat, and the relevant
authenticated Dashboard projection. Run the change's verifier regression
against the deployed source to confirm unsupported factual criteria and
unproven repository-publication claims fail closed.

If activation or health verification fails, atomically restore the recorded
predecessor pointer and restart only the owner-session service. Confirm the
predecessor is active and healthy. Keep both immutable release directories,
the rollback record, and all objective, artifact, and event history.

## Read-only health check

Run as an operator with permission to inspect systemd and use a read-only PostgreSQL identity:

```sh
systemctl show riverview-grace-execution.service -p ActiveState -p SubState -p MainPID
journalctl -u riverview-grace-execution.service --since=-15m --no-pager
psql "$RIVERVIEW_READONLY_DSN" -X -v ON_ERROR_STOP=1 -c "SELECT service_id,status,last_heartbeat_at,last_cycle_at,last_error_type,cycles_completed FROM riverview_dev.grace_execution_health"
```

Expected: `ActiveState=active`, `SubState=running`, a recent `last_heartbeat_at`, and `status=healthy`. The observed heartbeat is stale after the configured dashboard threshold; no row means `not_initialized`, not healthy. Logs contain failure classes and durable IDs only, never bearer credentials, objective request bodies, or artifact contents.

## Luna supervisory evaluation and recovery

Use authenticated Comms5 supervisory status to read the active grant, exact
function/provider scope, request count, settled spend, unresolved cost, and
available balance before retrying. CME recovery and performance evaluation
share only their explicitly authorized Luna scope. A provider response remains
advisory and cannot change objective scope, authorize work, or replace
independent verification.

The direct adapter's currently qualified output limit is 512 tokens for these
two structured request types. Larger 2048/4096-token requests returned provider
HTTP 400, while a 512-token request was accepted; the successful 512-token
performance response was truncated, so its retry uses compact schema
instructions. Retry selection is durable and idempotent: performance evaluation
gets one retry after a consumed JSON truncation, then one 512-token fallback if
that prior retry used more than 512 output tokens and failed at the provider.
A failed retry already at 512 tokens is terminal for that evaluation. CME
recovery may get one 512-token fallback after its bounded provider retries fail. Requests remain on the same
objective/correlation and active exact grant, with existing per-request and
total-budget checks. No retry is allowed after a valid result, if an equivalent
retry exists, after scope changes, or when authority/budget checks reject it.

Both JSON-mode request types use `text.format.type=json_object` and send their
unchanged serialized evidence in a user `input_text` message preceded by a
request-specific JSON instruction. For an HTTP error, the adapter records the
status, validated provider request ID, allowlisted provider error identifiers,
and a bounded sanitized message in the durable `provider_attempt_settled`
event. Raw response bodies and headers are not retained. A locally rejected
request has a distinct local failure type and does not represent a provider
response.

Verify successful evaluation through durable
`resident.performance.evaluation_recorded` and
`resident.performance.feedback_consumed` events, then confirm the authorized
Steward projection exposes the grade and feedback. An HTTP success, delivered
response, or Grace conversational claim is not a grade. For recovery, require
the persisted advisory-consumption event and retain the ordinary independent
verifier gate on the same assignment. Treat unknown provider errors and
unresolved API cost conservatively; do not infer zero spend from a failed
response without usage data.

## Request one verified-result rereview generation

The supported write path is the existing authenticated dashboard API:

```http
POST /api/v1/objectives/{objective_id}/result-rereview
Authorization: Bearer <existing dashboard API credential>
X-Riverview-Authority: <existing Steward objective.submit credential>
Content-Type: application/json

{"completion_cycle":1,"evidence_revision":"steward-evidence-rev-1","evidence":["One bounded, newly verified evidence item."],"idempotency_key":"grace-rereview:<objective-id>:cycle-1:revision-1"}
```

Use the existing approved authenticated client and protected credentials; do
not put credential bytes in shell history, command arguments, issue comments,
or logs. Immediately before the request, read the objective projection and
confirm the exact objective ID, accepted verifier completion cycle, and current
`objective.submit` grant on that objective's `scope_ref`. Evidence must be new,
bounded, and accurately described; the caller chooses a new stable evidence
revision and idempotency key. Do not replay a key with changed evidence.

Expected success is HTTP `202` with schema
`rv.grace.result-review-request.v1`, a generation number, evidence digest, and
`reused=false`. HTTP `202` means the durable request was accepted; it does not
mean Grace published a typed review or created s2. Confirm exactly one
`conversation.result_review_requested` event with the expected actor, scope,
completion cycle, revision, digest, and idempotency key. Then observe the
persistent Grace service consume and acknowledge the same generation. A
persisted dependent s2 is eligible after its dependencies are independently
accepted; a typed result-review decision is not an additional prerequisite.
Dispatch still passes unchanged verification, original scope, binding, and exact
`assignment.create` checks through CME; the API itself never dispatches.

| Outcome | Meaning | Safe next action |
| --- | --- | --- |
| `403 objective_review_not_authorized` | Missing/revoked/wrong-scope `objective.submit` | Recheck grant ID and scope through the authorized authority view; do not substitute another credential. |
| `409 objective_review_rejected` | Objective, prior generation, or key state conflicts | Read durable objective events and review receipts; preserve the existing decision and choose no retry until state is understood. |
| `400 invalid_objective_review_request` | Shape, revision, evidence, or idempotency input is invalid | Correct the bounded request; use a new key only for genuinely new evidence. |
| `503 authority_unavailable` / `objective_review_unavailable` | Authority or pipeline could not safely complete | Leave objective unchanged; retry the exact same request and key only after service health recovers. |
| HTTP result missing/uncertain | Client may have lost the response after commit | Read the durable request event. If it exists, do not submit again; if absent, resend only the exact same body/key after verifying no event was committed. |

The request event is the audit receipt; the follow-up typed review receipt and
continuation event are separate evidence. Never call the Python pipeline
directly, write objective tables, use `form_and_queue_work`, or create an
assignment as a substitute for this route.

## Symptoms and recovery

| Symptom | Likely cause / first check | Safe recovery | Verify / escalation |
| --- | --- | --- | --- |
| `resident.performance.evaluation_blocked` follows `external_reasoning.grace_consumed` | Read the sanitized log fields `objective_id`, `assignment_id`, `request_id`, `correlation_id`, `failure_stage`, and `reason_code`; inspect only the matching exchange's delivery state, response digest/provenance, and evaluation events. | Correct only the bounded consumer validation defect. The owner cycle replays the same already-consumed response under the existing exchange authorization; it does not call Luna. | Require exactly one matching `evaluation_recorded` and one `feedback_consumed` event with the original response digest. Provider attempt count, usage, cost and stored response must remain unchanged. If diagnostics identify an unrecognized schema or correlation mismatch, keep the evaluation blocked. |
| S4 artifact claims evaluation evidence is missing while the exchange is consumed | Compare the exact assignment's rework verification ID to the server-derived `performance_evaluation_runtime_evidence_for_assignment` correlation and feedback event IDs. | Replay the exact consumed evaluation first; issue the one-use exception only after the expected request is durably graded and its feedback-consumed event is present. Let only the exact assigned Codex rework receive the bounded evidence. Do not grant the worker database/provider access or rewrite the rejected artifact. | Independently verify request/correlation/response IDs, response digest, actual usage/cost, grade and both durable event IDs. The artifact must state the advisory grants no approval or execution authority. |
| CME proposes another diagnostic for an assignment held at `retry_limit_exhausted` | Check that the same current verifier ID has a durable escalation hold and that the assignment's `REWORK_PROPOSED` count is at least the configured limit. | The CME admission path suppresses only this exhausted assignment. Do not clear counters or create another stall identity. Recoverable stalls below the bound remain eligible for their existing diagnostics. | Confirm no new exchange or provider-attempt event was admitted for the exhausted assignment and that unrelated eligible work continues. |
| S4 is held at `retry_limit_exhausted` after three rework proposals | Check the current S4 verifier ID, assignment state, objective revision, and the exact `engineering.rework_retry_authorized` event and expiry. | Only the existing exact-scope single-use Steward authorization may queue the one S4 correction. It is consumed atomically with the ready transition; the ordinary three-attempt cap and past events remain unchanged. | Require one grant, one consumption, the same assignment under a new lease generation, preserved predecessor artifact, and a fresh independent verifier result. Any scope/revision/rejection mismatch remains held. |
| Unit exits during startup | Check sanitized `grace_service_configuration_error` or `grace_service_start_failed`; inspect unit environment and migration version. | Correct the exact missing non-secret setting or protected credential file through the authorized provisioning process. Do not edit live DB grants by hand. | Re-read health and journal; escalate missing/ambiguous grants to Steward/authority owner. |
| `grace_heartbeat_write_failed` or `grace_execution_cycle_failed` with `InsufficientPrivilege` | The restricted runtime role lacks the selected objective/event and health columns. Inspect only `has_column_privilege` for required columns and verify migration `0007_grace_runtime_objective_and_health_acl` checksum in `riverview_dev.schema_migrations`; do not read objective or conversation data to diagnose ACLs. | After a protected backup and exact checksum preflight, apply only the reviewed additive resident-execution migration with the standard migration runner, then start/restart only the Grace owner-session unit. It grants selected columns on `grace_objectives`, `grace_objective_events`, the one required event sequence, and `grace_execution_health`. It grants no event update/delete, objective identity update, unrelated table DML, or protected authority access. | Require `_proposed()`/objective projections to return without privilege errors, a fresh healthy heartbeat with `last_error_type IS NULL`, and a working restricted-role dashboard projection. If the relation, role, or checksum differs, stop and retain diagnostics. |
| Objective remains `WAITING_FOR_EVIDENCE` | Read only evidence status, source revision/hash, reference count, retrieval flag and selection-policy metadata. An `INCOMPLETE` result with verified source revision/hash but no selected value can mean relevant passages exceeded the context budget; do not print the objective or conversation body to diagnose it. | Confirm the package-pinned source set is intact. The resident selector verifies the complete allowlisted corpus, then deterministically ranks whole matching paragraphs within a 7 KiB selection budget; full source references and digest remain recorded. If no whole passage fits, leave the objective pending. After a provider correction, retry the same authenticated source message with blank criteria through the origin-idempotent intake route. A VERIFIED retry must atomically persist the evidence and transition the same row from `WAITING_FOR_EVIDENCE` to `GROUNDED`; if it does not, inspect the objective revision and the grounded/waiting events before any repeated retry. | Expect the same objective ID. It may advance only after `VERIFIED` grounding with complete source retrieval. Bounded selection metadata distinguishes full corpus verification from the subset passed to reasoning. Missing or oversized evidence cannot be overridden. |
| Website reports an intake conflict after a retry | Inspect objective status and `objective.received` origin metadata only; do not read the conversation body. A committed objective may exist while grounding waits. Confirm the active dashboard release and served asset identity. | Do not create a replacement objective or edit the ledger. For the same authenticated source, the endpoint revalidates `objective.submit`, preserves the original recorded criteria, and retries grounding; the criteria field may be blank. Retry-entered criteria never rewrite the existing objective. New sources still require criteria. | Expect the same objective ID and a `202` receipt with its current state. `work_order_origin_conflict` denotes a different source binding or ambiguous origin; authorization denial remains 403. A wait receipt is not a proposal, assignment, or approval. |
| Grounded conversation objective has no proposal | Inspect sanitized `resident_reasoning_cycle_failed` events and current office binding/provider identifiers; do not use conversation bodies from logs. | Confirm router digest matches the active binding and approved 80B readiness is `READY`; correct configuration only through the authorized release process. | Persistent service retries; any proposal must carry 80B provider/model provenance. Smaller models cannot propose Engineering work. |
| Objective completed but source conversation has no result | Inspect `objective.completed`, `conversation.result_published`, current Grace binding, and the `grace_result_review_deferred` event for readiness state, provider, model, elapsed time, bounded error code, finish reason, and completion-token limit. These fields contain no request/response text. Use the authenticated API for metadata-only conversation inspection. | The structured review uses `RIVERVIEW_GRACE_RESULT_REVIEW_TOKENS` (default 512, allowed 16–512). If diagnostics show `response_incomplete` with `finish_reason=length`, confirm the effective limit and correct it within that range; never accept a truncated response or manually mark the outbox published. | Next service cycle retries. Deterministic response identity prevents a duplicate assistant event after a successful insert. |
| `grace_conversation_result_return_failed` repeats after the response was published | Inspect the failed cycle's `objective_id`, `completion_cycle`, and whether exactly one matching `conversation.result_published` event exists. Use metadata-only objective events; do not inspect conversation bodies. | The durable outbox cycle is the acknowledgement identity. The service fills it from persisted context when the publisher omits it and rejects a publisher-supplied mismatch. Preserve the response and event history; do not manually acknowledge or delete/replay records. | After a reviewed release, retry the same outbox cycle. A matching durable publication event removes it from the next poll; the deterministic response identity prevents a duplicate assistant message. |
| `grace_conversation_result_return_failed` reports `failure_stage=resident_result_review` and `ValueError` at the review context-shape guard | Check the sanitized `failure_location` and confirm the deployed source contains the optional `artifact_review_unavailable` contract field. Inspect only artifact capability and availability status; do not inspect message text or credentials. | The result outbox may attach `artifact_review_unavailable` as null or `integrity_check_failed`. The 80B review accepts only those values. If bytes are unavailable, pass verifier metadata only; never trust or reconstruct artifact text. | Deploy a reviewed compatible service/provider pair, then retry the same durable cycle. Verify the resulting assistant receipt and one `conversation.result_published` event; the deterministic request ID prevents duplicate publication. |
| `grace_conversation_result_return_failed` reports `failure_stage=resident_result_review` at the structured decision parser | Check the adjacent `grace_verified_result_review_rejected` event. It records only a fixed validation stage, allowlisted decision value, expected-key presence, field types, and collection counts. Never log or copy generated rationale, prompts, proposed objectives, or raw provider output. | Correct the bounded prompt/output contract for the observed safe shape. Keep the exact decision set, field limits, scope checks, and typed continuation authorization. Do not accept malformed or truncated model output as a successful review. | Retry the same durable result cycle after a reviewed release. Confirm that a valid 80B decision is persisted once and the outbox acknowledgement is recorded. |
| A previously published result needs review after a new evidence revision | Read objective ID, completion cycle, latest review generation, request/published event keys, exact objective scope, and evidence digest from authorized objective metadata. Do not inspect or rewrite prior conversation decisions. A missing generation receipt with a durable conversation response is an acknowledgment-recovery case. | Through the authorized Grace pipeline caller only, submit one bounded evidence revision using the existing exact objective-scoped `objective.submit` grant, a new stable evidence revision identifier, and a new idempotency key. Repeated identical calls with the same key are safe; changed evidence with a reused key is rejected. Keys are globally unique across objective events, so a key already bound to another objective fails closed. The pending-review query filters out acknowledged cycles before applying its bounded batch limit; older completed reviews cannot starve a later pending generation. Do not write ledger events directly, reuse a review generation, broaden scope, or treat this grant as `assignment.create`. The mechanism caps each completion cycle at four generations. | Let the persistent service consume the durable request event. Confirm one matching `conversation.result_review_published` receipt with the same cycle, generation, evidence revision and digest; earlier receipts remain unchanged. A failed provider/binding/receipt check leaves the request pending for normal retry. Review requests never create or dispatch dependent work; only a separately valid exact-step decision can resume normal CME checks. This source path has not been commissioned as a production operator control. |
| Objective remains `PROPOSED` | Inspect `execution.dispatch_failed` event count and configured exact scope. Three failures stop automatic dispatch. | Correct service identity/scope/grant via governed authority provisioning. Do not manually change objective status. | Service will retry after restart only while below the three-failure cap. At cap, escalate and create a new authorized correction decision before resuming. |
| Grounded objective repeatedly emits `execution.reasoning_failed` with `failure_type=ObjectiveStateError` | Use authenticated Comms5 for objective state and lineage. Read only the matching `office:grace` reasoning outcome/plan through the existing authorized read path; compare the persisted candidate's step criteria with the immutable objective criteria. The known incomplete-criteria case records `detail_code=PROPOSAL_OMITS_ACCEPTANCE_CRITERIA`. Do not inspect or log prompts or raw model output. | Preserve the original objective and all criteria. Confirm the active office binding and approved reasoning provider/model identity. Deploy only the reviewed prompt correction that explicitly treats the prior plan as an unaccepted attempt and repeats negative constraints verbatim. Do not change the acceptance guard, create a proposal manually, or dispatch work. | Let the persistent owner-session poll the same grounded objective. Confirm a provider-generated complete proposal persists once as `work_order.proposed`, objective state becomes `PROPOSED`, and the proposal remains unapproved. Continue only through existing approval and exact `assignment.create` authorization. If the same omission repeats, stop repeated restarts and report the safe detail code and retained plan; do not bypass the guard. |
| Assignment is queued | Confirm event processor service, assignment event, scope and worker registry. | Restore the existing event processor; do not manually set `ready` in a live schema. | Wait for its durable queued-to-ready transition, then confirm worker attempt/lease evidence. |
| Bounded artifact attempt has no result or verifier rejects the output set | Read the persisted objective-step artifact contract, capability on the worker attempt, result artifact identities/count, safe storage metadata, and sanitized verifier criteria. Do not infer a filename from the task name or inspect unrelated workspace files. | Preserve the same assignment and retry history. The bounded capability supports one to eight JSON artifacts only; it writes under assignment/artifact-derived opaque storage identities, enforces an 8 KiB aggregate limit, and never chooses a filename default. Repair the persisted proposal only through its normal authorized revision path; do not alter an existing assignment contract in place. | Expect exact contract equality and file-set equality, assignment/objective/step provenance, verified source lineage, owner/mode/size checks, and digest equality. Contract changes, missing/extra artifacts, unsupported media types, or unsafe paths fail closed; use existing bounded recovery only when the exact assignment and retry ceiling permit it. |
| Assignment is blocked after worker failure | Inspect assignment events, worker attempts, execution intent and CME attention projection. | Let existing lease recovery reconcile only when safe; this worker is classified `retry_safe`. Correct the action fault first. | The artifact action is content-idempotent. Unknown external effects must remain in the existing Steward wait path. |
| Codex reports `workspace_change_set_invalid` with no attempt or artifact | Inspect only the assignment's execution-intent failure class, attempt/result/verifier counts and assignment-bound artifact metadata. Codex CLI output and conversation bodies are not required. | The bounded artifact capability accepts only the exact artifact paths, names, media types, per-output size limits and criteria persisted for that assignment. Source changes require the separate `engineering.codex-cli-source-change.v1` capability, an explicit assignment path allowlist, an immutable base revision, patch digest/inventory, and passing fixed tests. | A typed `CodexActionFailure` can resume after lease expiry only when the objective provenance remains verified, no attempt/result/verifier/artifact exists, and the existing retry ceiling permits it. Recovery records the decision and normal claim-time exact grant validation runs again. Any existing artifact or generic unknown exception remains blocked for Steward review. |
| A concurrently dispatched Codex step fails with `persisted_work_order_provenance_required`, while a sibling is the objective's latest assignment | Read the objective ID, assignment `objective_ref`, persisted step's `assignment_id`, matching `work_order.dispatched` event, immutable evidence state, intent, lease expiry, and attempt/result/verifier/artifact counts. Do not treat `grace_objectives.assignment_id` as the provenance for every step or inspect private work content. | The owner cycle uses the existing bounded no-artifact recovery for the original assignment after lease expiry. It requires the exact durable step-to-assignment and proposal-event linkage; it does not create another assignment or edit objective state. | Confirm one recovery record for the current lease generation, the original assignment returning to `ready`, unchanged step dispatch count, and claim-time exact worker grants. If the step or dispatch-event link is missing or mismatched, recovery fails closed for Steward diagnosis. |
| A dependent Engineering step is not dispatched | Inspect `grace_objective_steps` status, assigned work-order ID, `depends_on`, and verifier decision for each predecessor. Do not dispatch by editing assignment state. | Only pending steps whose every dependency is independently `verified` are dispatchable. The durable objective-step assignment link resolves task content; the runtime workflow node may change during CME transitions. | Repair the original predecessor through normal lease/recovery and independent verification. The next service poll claims the next dependency-ready step. |
| Legacy Codex verifier rejected substantive content for missing exact wording | Preserve the verifier record. Confirm the deployed verifier revision and criteria in the assignment-linked verification row, then confirm Grace's review context includes the exact verifier evidence and a bounded artifact snapshot whose SHA-256 matches the stored result. | The independent verifier now checks authorized assignment/criteria binding, file identity, digest, owner/mode/size, pinned source/repository provenance and mandatory Markdown structure. It does not decide whether prose substantively meets the criteria. Grace's bound 80B reads the digest-reverified artifact and makes the substantive decision. | The owner cycle first records Grace's durable `OBJECTIVE_SATISFIED`, `REWORK_PROPOSED`, or `STEWARD_AUTHORIZATION_REQUIRED` decision. Satisfaction permits only same-attempt verifier recheck; a rework decision alone can requeue the same assignment after exact `assignment.create` authorization. Never erase the original rejection or auto-requeue it. If artifact bytes fail integrity checks, expose verifier evidence without the untrusted bytes and do not accept satisfaction. |
| Owner-session startup reports `grace_service_start_failed` with `AttributeError` before its healthy event | Confirm the active immutable source commit and compare the service's startup recovery hook with `CodexWorkAction.reconcile_retryable_no_artifact_failures`. Do not inspect objective or conversation bodies. | Deploy a reviewed immutable release whose service entry point calls `reconcile_codex_startup_recovery`; missing hooks now produce the bounded `codex_recovery_hook_unavailable` configuration error. Preserve the existing objective, lease, event history, and release predecessor. | Restart only the owner-session service after package and backup checks. The normal cycle may retry the same assignment only after its lease expires and the recovery coordinator proves verified objective provenance and absence of attempts, results, verifier decisions, and artifact. |
| Assignment awaits verification | Check successful attempt result and verifier registry/lease/service. | Restore the distinct verifier service identity and exact `assignment.verify` grant. | Only a separately recorded `ACCEPTED` decision permits objective completion. |
| All required steps are verified but objective remains open | Read the objective row, ordered step statuses, assignment states, independent verification decisions, and latest `objective.completed` event. | Let the existing Grace service run its completion reconciliation cycle. It completes from the persisted accepted step state after restart; no worker replay or new Steward grant is needed. | One terminal event is written atomically with `COMPLETED`. Conversation review/receipt events are post-completion delivery and cannot reverse objective state. |
| Verification failures reach three | Inspect objective `verification_failures`, the three `execution.verification_failed` events and verifier journal. | Correct verifier/runtime faults; the poller caps retries per attempt and proceeds to other candidates. Do not change the assignment state manually. | The item remains awaiting verification and objective remains incomplete until independent verification succeeds; escalate unresolved evidence integrity concerns. |
| Dashboard says Grace unavailable/stale | Check `/api/v1/status`, dashboard journal, migration presence and heartbeat age. | Restore dashboard/database connectivity; do not infer health from systemd active state alone. | Confirm the service instance, fresh heartbeat, objective detail, artifact digest and verification decision. |
| Process restart during work | Inspect the latest lease generation, execution intent, attempt/result and recovery record. | Start the supervised service; it reads PostgreSQL and CME reconciles expired leases. Do not replay a completion manually. | A preserved result proceeds to verification; a safe action may be requeued; uncertain effects stay blocked for Steward. |
| Codex capability reports unavailable before assignment | Check sanitized `codex_sandbox_unavailable`; run the bwrap probe and inspect the loaded per-executable AppArmor policy without changing the global namespace restriction. | Keep the objective durable and un-dispatched. Do not select a danger-full-access mode. The authorized `/usr/bin/bwrap` profile trial passed; direct `unshare` remains restricted by design. | Repeat `bwrap --unshare-net --ro-bind / / --proc /proc --dev /dev /bin/true` from the owner-session context. The owner-session unit must permit only `AF_INET AF_UNIX AF_NETLINK`; bubblewrap uses NETLINK_ROUTE to configure its isolated loopback device. If it fails, preserve the request and follow the sandbox rollback record in the commissioning guide. |
| Owner-session startup reports sanitized `ValueError` or authentication initialization fails before assignment | Inspect only sanitized failure classes, the explicit `RIVERVIEW_CODEX_HOME` path, its owner/mode, and the single-file systemd bind declaration. `HOME` is the service state root and must not be used to infer `CODEX_HOME`; never display auth contents or the full process environment. | Resolve `CODEX_HOME` from `RIVERVIEW_CODEX_HOME` under private service state. Pre-create its directory as `admin1:admin1` mode `0700` and an empty `auth.json` mount target as `admin1:admin1` mode `0600`; the read-only bind alone supplies the existing owner auth file in the service namespace. Do not copy or refresh the login. | Confirm the target is empty before staging, preserve its metadata predecessor, and verify the unit's single-file read-only bind and `ProtectHome=tmpfs`. Run the bounded adapter preflight in owner-session context. If the home escapes state or the mounted auth file is absent/writable, fail closed without consuming a retry. |
| Owner-session Codex preflight returns `codex_code_mode_host_missing` | Inspect the sanitized preflight code and executable package inventory. Never display auth contents or CLI environment. | Keep work pending. Install the reviewed Codex CLI package including executable `codex-code-mode-host`; when required, invoke the CLI with `--enable code_mode_host`. A zero exit without the authorized workspace change remains rejected. Do not copy or refresh the personal login from the service. | Validate the unit with `systemd-analyze verify` and run the bounded adapter preflight as the owner. If the companion binary or valid existing login is unavailable, record the exact readiness failure and do not consume another assignment retry. |
| Code Mode CLI exits but no artifact is produced and kernel journal records `codex-code-mode-host` SIGTRAP | Preserve the assignment; inspect only executable/PID trap metadata and sanitized provider event types. Do not read prompts or authentication files. | The pinned Code Mode host traps under `MemoryDenyWriteExecute=yes`; set `MemoryDenyWriteExecute=no` only on the owner-session unit. Keep bubblewrap workspace-write isolation, disabled network, AppArmor confinement, and systemd filesystem/address-family controls enabled. | Verify through a transient unit matching the owner service that each output exactly matches the assignment's persisted path set and declared types; independently validate the adapter result. Restore MDWE=yes only if Code Mode execution is intentionally disabled, leaving Engineering work blocked rather than consuming retries. |
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

### Accepted dependency and rework escalation

After independent `ACCEPTED`, inspect the objective's persisted step list and
confirm the next step's `depends_on` entries are verified. The persistent owner
loop dispatches that step through the normal CME intake on its next cycle. A
pending 80B summary or `ADDITIONAL_EVIDENCE_REQUIRED` summary is not a dispatch
gate. Expect the objective to remain `WORK_ORDER_CREATED` until every persisted
step has independently passed; never mark it complete manually.

For `REJECTED`, the Dashboard exposes the current verifier reason and only the
original step criteria may be named in a correction. The service permits three
correction proposals for one assignment. After three rejected correction
attempts, or when the rejection-review provider is unavailable, expect one
idempotent `engineering.rework_escalation_pending` event and a blocked,
actionable Dashboard item. Read its reason code, step ID, verification ID,
attempt count and `required_action`; do not manually queue work. For
`review_provider_uncommissioned` or `review_provider_unavailable`, restore or
commission the already authorized provider through its approved process and
allow the owner loop to resume review. For `retry_limit_exhausted`, a Steward
must decide the next scoped action; do not silently raise the bound or assume
an external reasoning provider is commissioned. Assignment, verification and
rejection history remains intact.

## W4 cycle ordering, criteria, and completion review

`GraceExecutionService.run_once()` advances existing dispatch, leased worker,
independent verification, completion reconciliation, and result publication
before grounded-objective or external reasoning requests that may wait on a
model/provider. This uses the existing owner-session cycle and fair
grounded-objective selector; it does not add a queue. The measured baseline
reasoning request took 54.912 seconds in the provider and 56.207 seconds end to
end. Ready work is therefore handled before that call in the same cycle. The
service heartbeat may still wait until the reasoning call returns; diagnose the
actual cycle order before changing any timeout.

When a typed proposal has one deliverable but also includes objective intake,
work-order, verification, completion, or conversation-return requirements,
check the durable `work_order.proposed` event's `system_owned_criteria` mapping.
Each original criterion must remain byte-for-byte present either on a real
Engineering step or as a lifecycle criterion mapped to a supported durable
event. A lifecycle-only criterion must not produce a receipt assignment.
Distinct deliverables and real dependencies still use multiple ordered steps.

For a Codex JSON artifact, inspect the independent verification criteria. A
parseable envelope is insufficient: `REJECTED`, failed, blocked, denied, or
equivalent authoritative negative outcomes reject the artifact. Exact-literal
checks read deliverable content, not echoed `acceptance_criteria` or provenance
metadata. These checks establish integrity, required structure, and explicitly
testable literals only; Grace's reasoning decision remains responsible for
substantive acceptance.

Objective completion is governed by persisted state: the objective reaches
`COMPLETED` only when every required step is verified and has persisted
independent verification with decision `ACCEPTED`. The normal reconciliation
path records one durable `objective.completed` event idempotently and recovers
after interrupted processing. Grace's conversational `OBJECTIVE_COMPLETE`
response, other conversation messages, and published conversation feedback do
not determine or override objective completion. Preserve receipts and continue
only through the established evidence, continuation, or Steward-action path
when required. Do not modify objective state manually or replay the original
smoke test.

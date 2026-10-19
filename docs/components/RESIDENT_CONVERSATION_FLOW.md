<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_CONVERSATION_FLOW.md
Component: RESIDENT-CONVERSATION
File Revision: 1.0.23
Purpose: Generated focused flow for persistent Grace browser conversation
Authority: Canonical graph JSON; diagram generated and not hand-edited
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Register generated chat workflow view
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Add the canonical generated diagram slot
History: process_graphs/resident-conversation/browser-chat.json
-->
# Grace conversation flow

**Document Revision:** 1.0.0
**Generated from:** `process_graphs/resident-conversation/browser-chat.json`; do not edit Mermaid by hand.

```mermaid
flowchart LR
  subgraph g_rv_resident_conversation_browser_chat["RESIDENT-CONVERSATION / resident.conversation.v1"]
    g_rv_resident_conversation_browser_chat_browser_submit_e4a0bb86(["Authenticated browser submits a bounded conversation turn"])
    g_rv_resident_conversation_browser_chat_dashboard_auth_1ec7b499["Require existing dashboard bearer before resident API access"]
    g_rv_resident_conversation_browser_chat_exact_grant_77017003{"Does the human principal hold the exact office conversation grant?"}
    g_rv_resident_conversation_browser_chat_deny_c9c85a36[["Reject request without persisting or invoking a model"]]
    g_rv_resident_conversation_browser_chat_office_binding_47296b90["Read current bound occupant and model implementation through AuthorityRegistry"]
    g_rv_resident_conversation_browser_chat_provider_match_6e2180eb{"Does the registered provider match the exact implementation revision?"}
    g_rv_resident_conversation_browser_chat_model_readiness_diagnostic_90a0703b["Optional read-only readiness probe verifies health and exact served model; HTTP unavailability does not identify host power state"]
    g_rv_resident_conversation_browser_chat_persist_user_50079953["Append user event and idempotency key before inference"]
    g_rv_resident_conversation_browser_chat_context_bound_672d08c9["Assemble recent history; preserve system context and active turn, trim oldest eligible conversation context to the exact serialized 32 KiB provider limit, and reject irreducible protected-context overflow before inference"]
    g_rv_resident_conversation_browser_chat_stage_context_policy_b35672ba["Apply model-stage context policy and retain full canonical identity context for substantive stages"]
    g_rv_resident_conversation_browser_chat_inference_8bca7614["Call the office-bound local model adapter; only loopback or explicitly allowlisted OCTO1 routes are accepted, with served-model and binding checks"]
    g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79[["Persist a sanitized unavailable or incomplete response outcome"]]
    g_rv_resident_conversation_browser_chat_binding_recheck_06e5ffdc["Reject a result if the office implementation changed during inference"]
    g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b["Append one terminal response with actual served model and original plus executing implementation provenance"]
    g_rv_resident_conversation_browser_chat_restart_recovery_57f09430["After service restart mark unfinished request interrupted without automatic duplicate inference"]
    g_rv_resident_conversation_browser_chat_browser_history_c2d99277(["Return durable response/status and refresh the active conversation for later verified Engineering results"])
    g_rv_resident_conversation_browser_chat_future_objective_jump_be36018d["Future explicit authorization remains a separate objective submission path"]
    g_rv_resident_conversation_browser_chat_browser_render_ce223021["Render complete persisted messages with role, status, timestamp and provenance"]
    g_rv_resident_conversation_browser_chat_composer_47498ab0["Keep an editable local draft; Enter submits and Shift+Enter inserts a line break"]
    g_rv_resident_conversation_browser_chat_chat_details_710b7072["Show persisted conversation metadata with local and UTC timestamps"]
    g_rv_resident_conversation_browser_chat_message_actions_c4e90ab2["Allow local copy and detail inspection without forwarding private content"]
    g_rv_resident_conversation_browser_chat_responsive_a11y_4d7e53d6["Keep message text and controls accessible on narrow and desktop viewports"]
    g_rv_resident_conversation_browser_chat_session_present_9bde9509{"Does this browser have an authenticated linked Steward session or a legacy conversation cookie?"}
    g_rv_resident_conversation_browser_chat_session_connect_2f037c66["Validate both exact grants through the linked Steward principal or retained legacy credential"]
    g_rv_resident_conversation_browser_chat_session_cookie_158419c1["Revalidate linked account session and exact grants on every request; legacy cookie also remains supported"]
    g_rv_resident_conversation_browser_chat_auth_denial_latch_1556f60c[["Pause automatic history requests after 403 until explicit reconnect"]]
    g_rv_resident_conversation_browser_chat_readiness_route_7e67f750{"Route substantive turns to 80B; exact acknowledgments to 0.6B; narrow simple facts to provisional 30B"}
    g_rv_resident_conversation_browser_chat_attempt_diagnostics_6b1cc0a3["Emit sanitized provider attempts with bounded timing and error codes; never include conversation text"]
    g_rv_resident_conversation_browser_chat_defer_reasoning_7d693ff6["Persist complex turn and required capability when 80B is unavailable or busy"]
    g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14["Poll only due durable deferred turns, claim a cross-process lease, preserve original request/capability identity, apply persistent bounded retry scheduling, and atomically publish one correlated assistant response"]
    g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2[["Record sanitized readiness/completion diagnostics; deterministic provider errors are terminal while transient provider errors retain durable deferred work under the retry budget"]]
    g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca["Revalidate the original sender exact grant and current Grace occupant"]
    g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484{"Does the current binding match or follow the explicitly authorized direct router transition for the persisted capability?"}
    g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de[["Keep the request deferred when grant, capability, successor, or audited transition is invalid"]]
    g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f["Constrain the resumed turn to its persisted required capability; a deferred 80B turn uses only 80B regardless of later conversation turns"]
    g_rv_resident_conversation_browser_chat_grace_role_context_dbeb08cc["Inject shared canonical Director of Operations identity, responsibilities and no-permission boundary into ordinary and resumed turns"]
    g_rv_resident_conversation_browser_chat_operations_snapshot_a7547e58["Attach a bounded read-only CME, assignment, objective, worker and attention snapshot with freshness and redaction provenance"]
    g_rv_resident_conversation_browser_chat_stream_capability_check_1c5ad149{"Does this browser support authenticated fetch streaming?"}
    g_rv_resident_conversation_browser_chat_stream_submit_10a9739e["Persist the user turn and idempotency key, then return queued status without waiting for inference."]
    g_rv_resident_conversation_browser_chat_stream_events_3110d0b1["Persist bounded provider text deltas and sanitized queued/generating/completed/failed state."]
    g_rv_resident_conversation_browser_chat_stream_authorized_sse_9ad92368["Replay durable response events over same-origin authenticated SSE after a monotonic sequence cursor."]
    g_rv_resident_conversation_browser_chat_stream_render_dc01ef84["Render arriving text safely in the original conversation and measure first-text and delivery latency."]
    g_rv_resident_conversation_browser_chat_stream_reconnect_388d817d["Reconnect from the monotonic cursor; clear superseded partial generations and deferred text without duplicating terminal history."]
    g_rv_resident_conversation_browser_chat_stream_history_verify_0f5110ca["Load the canonical completed response from history after reload; stream and conversation terminal state commit atomically."]
    g_rv_resident_conversation_browser_chat_stream_nonstream_fallback_c2c28c67["Use the existing bounded synchronous conversation route when browser streaming is unavailable."]
    g_rv_resident_conversation_browser_chat_stream_failure_f82a9aa6[["Retain the user turn and one sanitized terminal failure; do not expose prompts, output logs, or credentials."]]
    g_rv_resident_conversation_browser_chat_provider_error_classification_00b2aa90{"Is this a transient readiness/transport/server failure, or a deterministic request/authentication/response failure?"}
    g_rv_resident_conversation_browser_chat_deferred_retry_budget_cd9dc00c["Persist retry attempt and next-attempt time; use 5/10/20/40 second delays and block after five automatic resume attempts while retaining the original request"]
    g_rv_resident_conversation_browser_chat_deferred_retry_blocked_785d668a[["Keep the correlated user request and response_deferred event durable; expose blocked status and stop automatic retries after exhaustion or authority denial"]]
    g_rv_resident_conversation_browser_chat_required_tool_context_23ba6950{"Does this 80B request require a current Comms5 lookup? Include only the selected tool schema; omit all tool schemas for ordinary reasoning."}
  end
  g_rv_grace_operational_integration_objective_intake_55567c14["Registered target<br/>rv:grace:operational-integration"]
  g_rv_resident_conversation_browser_chat_browser_submit_e4a0bb86 --> g_rv_resident_conversation_browser_chat_dashboard_auth_1ec7b499
  g_rv_resident_conversation_browser_chat_dashboard_auth_1ec7b499 --> g_rv_resident_conversation_browser_chat_exact_grant_77017003
  g_rv_resident_conversation_browser_chat_exact_grant_77017003 -->|diagnostic_branch: No exact active read/send grant| g_rv_resident_conversation_browser_chat_deny_c9c85a36
  g_rv_resident_conversation_browser_chat_exact_grant_77017003 -->|Authorized| g_rv_resident_conversation_browser_chat_office_binding_47296b90
  g_rv_resident_conversation_browser_chat_office_binding_47296b90 --> g_rv_resident_conversation_browser_chat_provider_match_6e2180eb
  g_rv_resident_conversation_browser_chat_provider_match_6e2180eb -->|diagnostic_branch: Provider or model revision unavailable| g_rv_resident_conversation_browser_chat_deny_c9c85a36
  g_rv_resident_conversation_browser_chat_provider_match_6e2180eb -->|Current implementation matched| g_rv_resident_conversation_browser_chat_persist_user_50079953
  g_rv_resident_conversation_browser_chat_provider_match_6e2180eb -->|documentation: Read-only readiness probe is available for diagnostics; chat currently requires no probe preflight| g_rv_resident_conversation_browser_chat_model_readiness_diagnostic_90a0703b
  g_rv_resident_conversation_browser_chat_persist_user_50079953 --> g_rv_resident_conversation_browser_chat_context_bound_672d08c9
  g_rv_resident_conversation_browser_chat_context_bound_672d08c9 -->|diagnostic_branch: Protected system context plus active user turn still exceeds 32 KiB; provider is not called| g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79
  g_rv_resident_conversation_browser_chat_inference_8bca7614 -->|diagnostic_branch: Timeout, unavailable or incomplete response| g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79
  g_rv_resident_conversation_browser_chat_inference_8bca7614 --> g_rv_resident_conversation_browser_chat_binding_recheck_06e5ffdc
  g_rv_resident_conversation_browser_chat_binding_recheck_06e5ffdc -->|diagnostic_branch: Office binding changed during inference| g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79
  g_rv_resident_conversation_browser_chat_binding_recheck_06e5ffdc -->|Same current binding| g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b
  g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b --> g_rv_resident_conversation_browser_chat_browser_history_c2d99277
  g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79 --> g_rv_resident_conversation_browser_chat_browser_history_c2d99277
  g_rv_resident_conversation_browser_chat_restart_recovery_57f09430 -->|recovery_route| g_rv_resident_conversation_browser_chat_browser_history_c2d99277
  g_rv_resident_conversation_browser_chat_browser_history_c2d99277 -->|documentation: Conversation does not promote work| g_rv_resident_conversation_browser_chat_future_objective_jump_be36018d
  g_rv_resident_conversation_browser_chat_future_objective_jump_be36018d -->|jump: Separate explicit objective path; no conversation-triggered call| g_rv_grace_operational_integration_objective_intake_55567c14
  g_rv_resident_conversation_browser_chat_browser_history_c2d99277 --> g_rv_resident_conversation_browser_chat_browser_render_ce223021
  g_rv_resident_conversation_browser_chat_browser_render_ce223021 --> g_rv_resident_conversation_browser_chat_composer_47498ab0
  g_rv_resident_conversation_browser_chat_browser_render_ce223021 --> g_rv_resident_conversation_browser_chat_chat_details_710b7072
  g_rv_resident_conversation_browser_chat_browser_render_ce223021 --> g_rv_resident_conversation_browser_chat_message_actions_c4e90ab2
  g_rv_resident_conversation_browser_chat_browser_render_ce223021 -->|verification| g_rv_resident_conversation_browser_chat_responsive_a11y_4d7e53d6
  g_rv_resident_conversation_browser_chat_dashboard_auth_1ec7b499 --> g_rv_resident_conversation_browser_chat_session_present_9bde9509
  g_rv_resident_conversation_browser_chat_session_present_9bde9509 -->|Cookie present| g_rv_resident_conversation_browser_chat_session_cookie_158419c1
  g_rv_resident_conversation_browser_chat_session_present_9bde9509 -->|diagnostic_branch: No linked Steward session or legacy cookie; explicit legacy Connect remains available| g_rv_resident_conversation_browser_chat_session_connect_2f037c66
  g_rv_resident_conversation_browser_chat_session_cookie_158419c1 --> g_rv_resident_conversation_browser_chat_exact_grant_77017003
  g_rv_resident_conversation_browser_chat_session_connect_2f037c66 --> g_rv_resident_conversation_browser_chat_exact_grant_77017003
  g_rv_resident_conversation_browser_chat_deny_c9c85a36 --> g_rv_resident_conversation_browser_chat_auth_denial_latch_1556f60c
  g_rv_resident_conversation_browser_chat_auth_denial_latch_1556f60c -->|recovery_route: User reconnects with an authorized credential| g_rv_resident_conversation_browser_chat_session_connect_2f037c66
  g_rv_resident_conversation_browser_chat_inference_8bca7614 --> g_rv_resident_conversation_browser_chat_readiness_route_7e67f750
  g_rv_resident_conversation_browser_chat_readiness_route_7e67f750 -->|Provider selected; begin bounded inference attempt| g_rv_resident_conversation_browser_chat_attempt_diagnostics_6b1cc0a3
  g_rv_resident_conversation_browser_chat_attempt_diagnostics_6b1cc0a3 -->|Success or authorized interim fallback; persist served provider and attempts| g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b
  g_rv_resident_conversation_browser_chat_attempt_diagnostics_6b1cc0a3 -->|diagnostic_branch: Required provider failed or is unavailable; keep request durable| g_rv_resident_conversation_browser_chat_defer_reasoning_7d693ff6
  g_rv_resident_conversation_browser_chat_readiness_route_7e67f750 -->|80B ready or bounded provisional path selected| g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b
  g_rv_resident_conversation_browser_chat_readiness_route_7e67f750 -->|diagnostic_branch: Substantive turn requires unavailable or busy 80B| g_rv_resident_conversation_browser_chat_defer_reasoning_7d693ff6
  g_rv_resident_conversation_browser_chat_defer_reasoning_7d693ff6 -->|recovery_route: Automatic readiness polling; durable request retained| g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14
  g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14 -->|diagnostic_branch: A resumed completion or readiness attempt failed; classify the sanitized code| g_rv_resident_conversation_browser_chat_provider_error_classification_00b2aa90
  g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14 -->|Lease acquired; inspect original principal and deferred capability| g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca
  g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca -->|diagnostic_branch: Original exact grant revoked or current occupant differs| g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de
  g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca -->|Exact grant and occupant revalidated| g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484
  g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484 -->|diagnostic_branch: No exact binding or explicit direct-upgrade compatibility| g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de
  g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484 -->|Authorized implementation continuity passed; enforce the original deferred capability| g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f
  g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de -->|recovery_route: Leave deferred request durable; resume only after an authorized correction| g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2
  g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f -->|diagnostic_branch: Required 80B unavailable or provider failed; leave pending without 30B or 0.6B substitution| g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2
  g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f -->|verification: 80B inference accepted and actual served-model provenance persisted under the original request| g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b
  g_rv_resident_conversation_browser_chat_context_bound_672d08c9 --> g_rv_resident_conversation_browser_chat_grace_role_context_dbeb08cc
  g_rv_resident_conversation_browser_chat_grace_role_context_dbeb08cc -->|Use existing read-only institutional projections; do not expose direct database or action tools| g_rv_resident_conversation_browser_chat_operations_snapshot_a7547e58
  g_rv_resident_conversation_browser_chat_operations_snapshot_a7547e58 -->|Router applies the selected capability's bounded context policy before provider invocation| g_rv_resident_conversation_browser_chat_stage_context_policy_b35672ba
  g_rv_resident_conversation_browser_chat_stage_context_policy_b35672ba -->|diagnostic_branch: Malformed context or no current user turn; reject before inference| g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79
  g_rv_resident_conversation_browser_chat_browser_submit_e4a0bb86 --> g_rv_resident_conversation_browser_chat_stream_capability_check_1c5ad149
  g_rv_resident_conversation_browser_chat_stream_capability_check_1c5ad149 -->|Streaming available; authenticated POST preserves original conversation and request IDs| g_rv_resident_conversation_browser_chat_stream_submit_10a9739e
  g_rv_resident_conversation_browser_chat_stream_capability_check_1c5ad149 -->|No stream support; use existing bounded response API| g_rv_resident_conversation_browser_chat_stream_nonstream_fallback_c2c28c67
  g_rv_resident_conversation_browser_chat_stream_submit_10a9739e -->|Idempotently persist before returning queued| g_rv_resident_conversation_browser_chat_persist_user_50079953
  g_rv_resident_conversation_browser_chat_persist_user_50079953 -->|Background generation uses the same authorization and routing checks| g_rv_resident_conversation_browser_chat_stream_events_3110d0b1
  g_rv_resident_conversation_browser_chat_stream_events_3110d0b1 -->|0.6B, provisional 30B, or 80B selected by existing router; image upload is not part of this route| g_rv_resident_conversation_browser_chat_inference_8bca7614
  g_rv_resident_conversation_browser_chat_stream_events_3110d0b1 -->|diagnostic_branch: Provider, authorization, or persistence failure| g_rv_resident_conversation_browser_chat_stream_failure_f82a9aa6
  g_rv_resident_conversation_browser_chat_stream_events_3110d0b1 -->|Atomic durable response and stream completion| g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b
  g_rv_resident_conversation_browser_chat_stream_authorized_sse_9ad92368 -->|Read authorized durable cursor events only| g_rv_resident_conversation_browser_chat_stream_events_3110d0b1
  g_rv_resident_conversation_browser_chat_stream_authorized_sse_9ad92368 -->|recovery_route: Disconnect or bounded 180-second stream closure| g_rv_resident_conversation_browser_chat_stream_reconnect_388d817d
  g_rv_resident_conversation_browser_chat_stream_reconnect_388d817d -->|Resume after last consumed sequence| g_rv_resident_conversation_browser_chat_stream_authorized_sse_9ad92368
  g_rv_resident_conversation_browser_chat_stream_authorized_sse_9ad92368 -->|Sanitized text chunks and status state| g_rv_resident_conversation_browser_chat_stream_render_dc01ef84
  g_rv_resident_conversation_browser_chat_stream_render_dc01ef84 --> g_rv_resident_conversation_browser_chat_browser_render_ce223021
  g_rv_resident_conversation_browser_chat_browser_history_c2d99277 -->|verification: Reload canonical persisted response; no preview duplicates| g_rv_resident_conversation_browser_chat_stream_history_verify_0f5110ca
  g_rv_resident_conversation_browser_chat_stream_nonstream_fallback_c2c28c67 --> g_rv_resident_conversation_browser_chat_context_bound_672d08c9
  g_rv_resident_conversation_browser_chat_stream_failure_f82a9aa6 --> g_rv_resident_conversation_browser_chat_browser_history_c2d99277
  g_rv_resident_conversation_browser_chat_provider_error_classification_00b2aa90 -->|diagnostic_branch: Deterministic prompt, authorization, request, model-identity or malformed-response failure| g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79
  g_rv_resident_conversation_browser_chat_provider_error_classification_00b2aa90 -->|diagnostic_branch: Transient timeout/transport/loading/busy, HTTP 408/409/425/429, or any 5xx failure| g_rv_resident_conversation_browser_chat_deferred_retry_budget_cd9dc00c
  g_rv_resident_conversation_browser_chat_deferred_retry_budget_cd9dc00c -->|recovery_route: A scheduled retry is due and fewer than five automatic attempts have failed| g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14
  g_rv_resident_conversation_browser_chat_deferred_retry_budget_cd9dc00c -->|diagnostic_branch: Five automatic attempts exhausted; retain durable request and expose blocked state| g_rv_resident_conversation_browser_chat_deferred_retry_blocked_785d668a
  g_rv_resident_conversation_browser_chat_stage_context_policy_b35672ba -->|Select only the exact required internal tool schema after request matching| g_rv_resident_conversation_browser_chat_required_tool_context_23ba6950
  g_rv_resident_conversation_browser_chat_required_tool_context_23ba6950 -->|No current lookup is required; omit the internal tool catalog| g_rv_resident_conversation_browser_chat_inference_8bca7614
  g_rv_resident_conversation_browser_chat_required_tool_context_23ba6950 -->|Current lookup is required; include only the selected schema| g_rv_resident_conversation_browser_chat_inference_8bca7614
  g_rv_resident_conversation_browser_chat_required_tool_context_23ba6950 -->|diagnostic_branch: Protected context plus one selected schema cannot fit the exact provider byte limit; reject before inference| g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_CONVERSATION_FLOW.md
Component: RESIDENT-CONVERSATION
File Revision: 1.0.10
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
    g_rv_resident_conversation_browser_chat_context_bound_672d08c9["Assemble recent persisted history and reject serialized context above 32 KiB"]
    g_rv_resident_conversation_browser_chat_inference_8bca7614["Call the office-bound local model adapter; only loopback or explicitly allowlisted OCTO1 routes are accepted, with served-model and binding checks"]
    g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79[["Persist a sanitized unavailable or incomplete response outcome"]]
    g_rv_resident_conversation_browser_chat_binding_recheck_06e5ffdc["Reject a result if the office implementation changed during inference"]
    g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b["Append one terminal response with actual served model and original plus executing implementation provenance"]
    g_rv_resident_conversation_browser_chat_restart_recovery_57f09430["After service restart mark unfinished request interrupted without automatic duplicate inference"]
    g_rv_resident_conversation_browser_chat_browser_history_c2d99277(["Return durable response/status and render persisted conversation in dashboard"])
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
    g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14["Poll durable deferred turns, acquire a cross-process lease, and rebuild context only through the original request"]
    g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2[["Keep the request pending when the required 80B capability is unavailable; emit sanitized provider attempt diagnostics"]]
    g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca["Revalidate the original sender exact grant and current Grace occupant"]
    g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484{"Does the current binding match or follow the explicitly authorized direct router transition for the persisted capability?"}
    g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de[["Keep the request deferred when grant, capability, successor, or audited transition is invalid"]]
    g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f["Constrain the resumed turn to its persisted required capability; a deferred 80B turn uses only 80B regardless of later conversation turns"]
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
  g_rv_resident_conversation_browser_chat_context_bound_672d08c9 -->|diagnostic_branch: Context too large; model is not called| g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79
  g_rv_resident_conversation_browser_chat_context_bound_672d08c9 -->|Within context bound| g_rv_resident_conversation_browser_chat_inference_8bca7614
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
  g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14 -->|diagnostic_branch: Capability or provider remains unavailable| g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2
  g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2 -->|recovery_route: Retry persisted request when readiness changes| g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14
  g_rv_resident_conversation_browser_chat_resume_reasoning_55d48b14 -->|Lease acquired; inspect original principal and deferred capability| g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca
  g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca -->|diagnostic_branch: Original exact grant revoked or current occupant differs| g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de
  g_rv_resident_conversation_browser_chat_resume_auth_recheck_b0f115ca -->|Exact grant and occupant revalidated| g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484
  g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484 -->|diagnostic_branch: No exact binding or explicit direct-upgrade compatibility| g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de
  g_rv_resident_conversation_browser_chat_upgrade_continuity_a3e9f484 -->|Authorized implementation continuity passed; enforce the original deferred capability| g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f
  g_rv_resident_conversation_browser_chat_upgrade_rejected_183d47de -->|recovery_route: Leave deferred request durable; resume only after an authorized correction| g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2
  g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f -->|diagnostic_branch: Required 80B unavailable or provider failed; leave pending without 30B or 0.6B substitution| g_rv_resident_conversation_browser_chat_reasoning_router_failure_43c1e7f2
  g_rv_resident_conversation_browser_chat_resume_capability_pin_e7b3b64f -->|verification: 80B inference accepted and actual served-model provenance persisted under the original request| g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

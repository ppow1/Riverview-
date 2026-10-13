<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_CONVERSATION_FLOW.md
Component: RESIDENT-CONVERSATION
File Revision: 1.0.3
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
    g_rv_resident_conversation_browser_chat_persist_user_50079953["Append user event and idempotency key before inference"]
    g_rv_resident_conversation_browser_chat_context_bound_672d08c9["Assemble recent persisted history and reject serialized context above 32 KiB"]
    g_rv_resident_conversation_browser_chat_inference_8bca7614["Call the current loopback model adapter; no tools or work-order operation exists"]
    g_rv_resident_conversation_browser_chat_provider_failure_64f2fd79[["Persist a sanitized unavailable or incomplete response outcome"]]
    g_rv_resident_conversation_browser_chat_binding_recheck_06e5ffdc["Reject a result if the office implementation changed during inference"]
    g_rv_resident_conversation_browser_chat_persist_response_dc11fb6b["Append assistant message with model and token provenance"]
    g_rv_resident_conversation_browser_chat_restart_recovery_57f09430["After service restart mark unfinished request interrupted without automatic duplicate inference"]
    g_rv_resident_conversation_browser_chat_browser_history_c2d99277(["Return durable response/status and render persisted conversation in dashboard"])
    g_rv_resident_conversation_browser_chat_future_objective_jump_be36018d["Future explicit authorization remains a separate objective submission path"]
    g_rv_resident_conversation_browser_chat_browser_render_ce223021["Render complete persisted messages with role, status, timestamp and provenance"]
    g_rv_resident_conversation_browser_chat_composer_47498ab0["Keep an editable local draft; Enter submits and Shift+Enter inserts a line break"]
    g_rv_resident_conversation_browser_chat_chat_details_710b7072["Show persisted conversation metadata with local and UTC timestamps"]
    g_rv_resident_conversation_browser_chat_message_actions_c4e90ab2["Allow local copy and detail inspection without forwarding private content"]
    g_rv_resident_conversation_browser_chat_responsive_a11y_4d7e53d6["Keep message text and controls accessible on narrow and desktop viewports"]
  end
  g_rv_grace_operational_integration_objective_intake_55567c14["Registered target<br/>rv:grace:operational-integration"]
  g_rv_resident_conversation_browser_chat_browser_submit_e4a0bb86 --> g_rv_resident_conversation_browser_chat_dashboard_auth_1ec7b499
  g_rv_resident_conversation_browser_chat_dashboard_auth_1ec7b499 --> g_rv_resident_conversation_browser_chat_exact_grant_77017003
  g_rv_resident_conversation_browser_chat_exact_grant_77017003 -->|diagnostic_branch: No exact active read/send grant| g_rv_resident_conversation_browser_chat_deny_c9c85a36
  g_rv_resident_conversation_browser_chat_exact_grant_77017003 -->|Authorized| g_rv_resident_conversation_browser_chat_office_binding_47296b90
  g_rv_resident_conversation_browser_chat_office_binding_47296b90 --> g_rv_resident_conversation_browser_chat_provider_match_6e2180eb
  g_rv_resident_conversation_browser_chat_provider_match_6e2180eb -->|diagnostic_branch: Provider or model revision unavailable| g_rv_resident_conversation_browser_chat_deny_c9c85a36
  g_rv_resident_conversation_browser_chat_provider_match_6e2180eb -->|Current implementation matched| g_rv_resident_conversation_browser_chat_persist_user_50079953
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
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

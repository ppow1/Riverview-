<!--
Riverview~ Controlled Document
File: docs/components/CHATGPT_DOORBELL_FLOW.md
Component: CHATGPT-DOORBELL
File Revision: 1.0.1
Purpose: Generated New-Core Linux doorbell process view
Changed: 2026-10-17 UTC | RV-C3-DOORBELL-001 | Register fixed browser wake workflow
-->
# ChatGPT Doorbell Flow

The browser workflow ends at verified fixed-message submission. Comms5 mailbox
and Grace response transitions remain an external dependency until the owner
contract is available; this graph does not represent them as implemented.

```mermaid
flowchart LR
  subgraph g_rv_chatgpt_doorbell_browser_runtime["CHATGPT-DOORBELL / chatgpt.doorbell.v1"]
    g_rv_chatgpt_doorbell_browser_runtime_request_identity_e27c3bb7(["Comms5-owned caller supplies one durable request and correlation identity"])
    g_rv_chatgpt_doorbell_browser_runtime_binding_check_70a09cfc["Require local conversation config to match the caller's current designated Comms5 binding"]
    g_rv_chatgpt_doorbell_browser_runtime_binding_failure_5a943dc9[["Reject a target mismatch before invoking the browser"]]
    g_rv_chatgpt_doorbell_browser_runtime_target_resolution_689ceaf5["Resolve exactly one configured ChatGPT conversation over localhost CDP"]
    g_rv_chatgpt_doorbell_browser_runtime_authenticated_composer_68021f6d{"Is the selected target authenticated and its composer available?"}
    g_rv_chatgpt_doorbell_browser_runtime_steward_login_62dddd20[["Steward completes supported login or MFA in the dedicated Riverview profile"]]
    g_rv_chatgpt_doorbell_browser_runtime_fixed_wake_f84be1d1["Submit only the fixed wake text with the allowlisted send control"]
    g_rv_chatgpt_doorbell_browser_runtime_submit_verification_ded1bd9a["Require click invocation and composer-cleared transition before recording success"]
    g_rv_chatgpt_doorbell_browser_runtime_metadata_result_1010d17f(["Return request/correlation identity and metadata-only evidence to the caller"])
  end
  g_rv_chatgpt_doorbell_browser_runtime_request_identity_e27c3bb7 --> g_rv_chatgpt_doorbell_browser_runtime_binding_check_70a09cfc
  g_rv_chatgpt_doorbell_browser_runtime_binding_check_70a09cfc -->|binding matches| g_rv_chatgpt_doorbell_browser_runtime_target_resolution_689ceaf5
  g_rv_chatgpt_doorbell_browser_runtime_binding_check_70a09cfc -->|diagnostic_branch: binding differs| g_rv_chatgpt_doorbell_browser_runtime_binding_failure_5a943dc9
  g_rv_chatgpt_doorbell_browser_runtime_target_resolution_689ceaf5 -->|one exact target| g_rv_chatgpt_doorbell_browser_runtime_authenticated_composer_68021f6d
  g_rv_chatgpt_doorbell_browser_runtime_target_resolution_689ceaf5 -->|diagnostic_branch: target missing or duplicated| g_rv_chatgpt_doorbell_browser_runtime_binding_failure_5a943dc9
  g_rv_chatgpt_doorbell_browser_runtime_authenticated_composer_68021f6d -->|ready| g_rv_chatgpt_doorbell_browser_runtime_fixed_wake_f84be1d1
  g_rv_chatgpt_doorbell_browser_runtime_authenticated_composer_68021f6d -->|escalation: authentication required| g_rv_chatgpt_doorbell_browser_runtime_steward_login_62dddd20
  g_rv_chatgpt_doorbell_browser_runtime_steward_login_62dddd20 -->|recovery_route: login completed; rerun preflight| g_rv_chatgpt_doorbell_browser_runtime_authenticated_composer_68021f6d
  g_rv_chatgpt_doorbell_browser_runtime_fixed_wake_f84be1d1 --> g_rv_chatgpt_doorbell_browser_runtime_submit_verification_ded1bd9a
  g_rv_chatgpt_doorbell_browser_runtime_submit_verification_ded1bd9a -->|verified submission| g_rv_chatgpt_doorbell_browser_runtime_metadata_result_1010d17f
  g_rv_chatgpt_doorbell_browser_runtime_submit_verification_ded1bd9a -->|diagnostic_branch: send transition not verified| g_rv_chatgpt_doorbell_browser_runtime_binding_failure_5a943dc9
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

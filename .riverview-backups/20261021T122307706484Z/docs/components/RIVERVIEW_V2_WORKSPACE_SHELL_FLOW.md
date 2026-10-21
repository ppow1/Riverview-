<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL_FLOW.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL · generated from canonical JSON
File Revision: 1.0.14
Purpose: Show LAN preview security, same-origin authenticated Grace chat, Comms5 diagnostics, snapshot, and recovery paths
Authority: Presentation-only process flow; edit canonical JSON graph only
Changed: 2026-10-21 UTC | RV-V2-CAPABILITY-INTEGRATION-P1 | Regenerate with read-only objective and assignment projections in Work
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell and Grace integration flow

**Task:** `RV-WEB-V2-SHELL-001` · **Component:** `RIVERVIEW-V2-WORKSPACE-SHELL`  
**Source:** canonical JSON `process_graphs/riverview-v2/workspace-shell.json`; Mermaid below is generated.

```mermaid
flowchart LR
  subgraph g_rv_riverview_v2_workspace_shell["RIVERVIEW-V2-WORKSPACE-SHELL / local-static-preview"]
    g_rv_riverview_v2_workspace_shell_open_preview_624fa602(["Start loopback or authenticated LAN preview"])
    g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e["Apply Host, client subnet, and password session checks before serving assets"]
    g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409["Render clearly labeled local preview fixtures"]
    g_rv_riverview_v2_workspace_shell_choose_view_161dc67b{"Choose Overview, fixture view, or a resident workspace"}
    g_rv_riverview_v2_workspace_shell_retain_context_f40171d8["Retain selected resident in browser memory across views"]
    g_rv_riverview_v2_workspace_shell_unsafe_method_4b803134[["Reject mutating preview methods and out-of-root paths"]]
    g_rv_riverview_v2_workspace_shell_restart_preview_b905f3f1["Restart preview, revoke sessions, and reset in-memory UI state"]
    g_rv_riverview_v2_workspace_shell_stop_preview_9aec5773(["Stop preview process without affecting V1"])
    g_rv_riverview_v2_workspace_shell_configure_password_23bdc8eb["Steward chooses password locally; write salted hash only"]
    g_rv_riverview_v2_workspace_shell_missing_hash_9814e1ef[["Refuse LAN startup without protected password hash"]]
    g_rv_riverview_v2_workspace_shell_check_client_4d1766d6{"Validate explicit Host and trusted LAN source subnet"}
    g_rv_riverview_v2_workspace_shell_reject_client_6ff3b5b5[["Reject wrong Host or client outside trusted subnet"]]
    g_rv_riverview_v2_workspace_shell_check_session_4f647f12{"Check eight-hour signed session cookie"}
    g_rv_riverview_v2_workspace_shell_password_form_cbec0a84["Serve uncached password form with trusted-LAN warning"]
    g_rv_riverview_v2_workspace_shell_verify_password_8b9303e1{"Validate exact Origin or consume a one-use CSRF token, then verify salted password hash"}
    g_rv_riverview_v2_workspace_shell_reject_login_csrf_58167d85[["Reject foreign Origin or missing, expired, replayed, or wrong-client CSRF token"]]
    g_rv_riverview_v2_workspace_shell_rate_limited_36c38b3d[["After five failures, return 429 and 15-minute Retry-After"]]
    g_rv_riverview_v2_workspace_shell_issue_session_29d7e2fd["Issue HttpOnly SameSite cookie signed by in-memory key"]
    g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d{"Choose theme or independent sidebar state"}
    g_rv_riverview_v2_workspace_shell_apply_theme_81b77d1d["Apply Light, Dark, or System theme; persist display preference only"]
    g_rv_riverview_v2_workspace_shell_cycle_sidebars_3ade16cc["Cycle left and right sidebars independently through expanded, compact, and hidden"]
    g_rv_riverview_v2_workspace_shell_restore_sidebars_f1b4862e["Restore a hidden sidebar using its accessible floating control"]
    g_rv_riverview_v2_workspace_shell_integration_unavailable_166ea227["Historical cross-origin chat barrier before authorized same-origin integration; not a current runtime state"]
    g_rv_riverview_v2_workspace_shell_snapshot_click_c7b14d94(["Click Snapshot in the active V2 view"])
    g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b["Capture the selected view and safe connection metadata without message contents"]
    g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec["Hash structured members and build bounded ZIP manifest"]
    g_rv_riverview_v2_workspace_shell_snapshot_download_2aeb1eaf["Download local ZIP; no network upload"]
    g_rv_riverview_v2_workspace_shell_snapshot_verify_0d5c9c66["Inspect ZIP members and hashes against active V2 state"]
    g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13[["Show local capture or package-bound failure without upload"]]
    g_rv_riverview_v2_workspace_shell_grace_chat_handoff_29224207["Retired cross-origin Dashboard handoff; the current V2 route uses same-origin authentication"]
    g_rv_riverview_v2_workspace_shell_comms5_unverified_fbb092d5["Keep Comms5 transport counts and inspectable message ledger UNVERIFIED when the authoritative event feed is absent"]
    g_rv_riverview_v2_workspace_shell_open_v2_route_83acf28c(["Open LAN-only same-origin HTTPS /v2/ while V1 root continues serving Dashboard"])
    g_rv_riverview_v2_workspace_shell_serve_v2_static_245d797e["Nginx serves versioned static V2 assets under inherited LAN, Host, TLS, and Origin controls"]
    g_rv_riverview_v2_workspace_shell_dashboard_session_62b93d74{"Check the existing Dashboard account session; request sign-in only when absent"}
    g_rv_riverview_v2_workspace_shell_dashboard_login_54af0cdd["Submit Dashboard credentials directly to the same-origin HTTPS login API; retain only server-issued cookies"]
    g_rv_riverview_v2_workspace_shell_grace_grants_a8bc5c23{"Dashboard verifies Steward identity and exact resident.conversation.read/send grants"}
    g_rv_riverview_v2_workspace_shell_grace_access_denied_ce390666[["Show authentication, CSRF, grant, or conversation-service denial without retrying a send"]]
    g_rv_riverview_v2_workspace_shell_grace_load_history_7240fd1d["Read authorized conversation index and durable selected history; store only selected conversation ID"]
    g_rv_riverview_v2_workspace_shell_grace_send_message_1990567d["Submit one typed message with a unique client message ID through the existing streamed conversation endpoint"]
    g_rv_riverview_v2_workspace_shell_grace_response_state_996c19ef{"Check durable response status and matched assistant event without inferring completion from acceptance"}
    g_rv_riverview_v2_workspace_shell_grace_reply_persisted_a711c1c3["Render real persisted Grace response, event sequence, timestamp, and durable history after reload"]
    g_rv_riverview_v2_workspace_shell_grace_recovery_a7678f56["Refresh durable history and resume read-only status checks; never automatically repeat uncertain send"]
    g_rv_riverview_v2_workspace_shell_route_resident_selection_89cc4007{"Choose selected resident: Grace or a synthetic preview record"}
    g_rv_riverview_v2_workspace_shell_render_grace_center_9f9b903c["Render authenticated Grace conversation in the center workspace; keep right panel contextual"]
    g_rv_riverview_v2_workspace_shell_communications_view_51b400cb["Render Communications Activity controls and safe summary in V2"]
    g_rv_riverview_v2_workspace_shell_communications_source_check_c3cffc2d{"Check whether an authorized redacted read-only Comms5 activity source is configured"}
    g_rv_riverview_v2_workspace_shell_communications_unverified_50cc0073["Keep source UNVERIFIED, counts unavailable, and ledger empty without implying zero traffic"]
    g_rv_riverview_v2_workspace_shell_communications_local_refresh_0f9e83ae["Refresh local source configuration state without sending an unauthenticated request"]
    g_rv_riverview_v2_workspace_shell_resource_monitor_view_55ba762e["Render V2 Hardware & AI Resource Monitor with per-source provenance"]
    g_rv_riverview_v2_workspace_shell_resource_dashboard_auth_60501e27{"Check existing same-origin Dashboard account session before reading status"}
    g_rv_riverview_v2_workspace_shell_resource_dashboard_status_e9c526f3["Read only rv.dashboard.status.v1 through authenticated GET /api/v1/status"]
    g_rv_riverview_v2_workspace_shell_resource_operational_projection_57d5cc51["Render timestamped Dashboard worker leases and institutional assignment counts separately from inference workloads"]
    g_rv_riverview_v2_workspace_shell_resource_unavailable_metrics_cb5fbbef{"Determine whether an approved timestamped host/model telemetry projection exists"}
    g_rv_riverview_v2_workspace_shell_resource_unavailable_state_5ec2a928["Keep GPU/model/queue metrics unavailable rather than zero when no authorized source exists"]
    g_rv_riverview_v2_workspace_shell_resource_filter_refresh_3d743915["Allow bounded manual refresh, local filters, and per-source details without background polling"]
    g_rv_riverview_v2_workspace_shell_resource_snapshot_redaction_41c4cee2["Capture only source availability metadata in Snapshot; omit hardware values and work counts"]
    g_rv_riverview_v2_workspace_shell_resource_telemetry_contract_c56ce823["Future same-origin timestamped read-only resource projection is documented but not implemented"]
  end
  g_rv_riverview_v2_workspace_shell_open_preview_624fa602 --> g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e
  g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e --> g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409
  g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409 --> g_rv_riverview_v2_workspace_shell_choose_view_161dc67b
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Select resident; context remains across views| g_rv_riverview_v2_workspace_shell_retain_context_f40171d8
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|diagnostic_branch: Unsafe method or path is attempted| g_rv_riverview_v2_workspace_shell_unsafe_method_4b803134
  g_rv_riverview_v2_workspace_shell_unsafe_method_4b803134 -->|recovery_route: Resume by restarting local preview if needed| g_rv_riverview_v2_workspace_shell_restart_preview_b905f3f1
  g_rv_riverview_v2_workspace_shell_retain_context_f40171d8 -->|Navigate while selected resident remains in memory| g_rv_riverview_v2_workspace_shell_choose_view_161dc67b
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Stop foreground preview| g_rv_riverview_v2_workspace_shell_stop_preview_9aec5773
  g_rv_riverview_v2_workspace_shell_configure_password_23bdc8eb -->|prerequisite: Required before non-loopback startup| g_rv_riverview_v2_workspace_shell_open_preview_624fa602
  g_rv_riverview_v2_workspace_shell_open_preview_624fa602 -->|diagnostic_branch: LAN mode requested without a protected password hash| g_rv_riverview_v2_workspace_shell_missing_hash_9814e1ef
  g_rv_riverview_v2_workspace_shell_missing_hash_9814e1ef -->|recovery_route: Create hash locally; restart after verification| g_rv_riverview_v2_workspace_shell_stop_preview_9aec5773
  g_rv_riverview_v2_workspace_shell_open_preview_624fa602 --> g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e
  g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e --> g_rv_riverview_v2_workspace_shell_check_client_4d1766d6
  g_rv_riverview_v2_workspace_shell_check_client_4d1766d6 -->|diagnostic_branch: Host or source subnet is outside policy| g_rv_riverview_v2_workspace_shell_reject_client_6ff3b5b5
  g_rv_riverview_v2_workspace_shell_reject_client_6ff3b5b5 -->|recovery_route: Correct URL/network or stop the preview| g_rv_riverview_v2_workspace_shell_stop_preview_9aec5773
  g_rv_riverview_v2_workspace_shell_check_client_4d1766d6 -->|Host and source address accepted| g_rv_riverview_v2_workspace_shell_check_session_4f647f12
  g_rv_riverview_v2_workspace_shell_check_session_4f647f12 -->|Valid signed cookie| g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409
  g_rv_riverview_v2_workspace_shell_check_session_4f647f12 -->|diagnostic_branch: No valid session| g_rv_riverview_v2_workspace_shell_password_form_cbec0a84
  g_rv_riverview_v2_workspace_shell_password_form_cbec0a84 -->|Steward submits password| g_rv_riverview_v2_workspace_shell_verify_password_8b9303e1
  g_rv_riverview_v2_workspace_shell_verify_password_8b9303e1 -->|Hash matches and Origin/CSRF checks pass| g_rv_riverview_v2_workspace_shell_issue_session_29d7e2fd
  g_rv_riverview_v2_workspace_shell_verify_password_8b9303e1 -->|diagnostic_branch: Origin mismatches or one-use CSRF token is invalid| g_rv_riverview_v2_workspace_shell_reject_login_csrf_58167d85
  g_rv_riverview_v2_workspace_shell_reject_login_csrf_58167d85 -->|recovery_route: Reload login page for a fresh token; retain strict Host check| g_rv_riverview_v2_workspace_shell_password_form_cbec0a84
  g_rv_riverview_v2_workspace_shell_issue_session_29d7e2fd --> g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409
  g_rv_riverview_v2_workspace_shell_verify_password_8b9303e1 -->|diagnostic_branch: Bad password; fifth failure in 15 minutes| g_rv_riverview_v2_workspace_shell_rate_limited_36c38b3d
  g_rv_riverview_v2_workspace_shell_rate_limited_36c38b3d -->|recovery_route: Wait Retry-After before trying again| g_rv_riverview_v2_workspace_shell_password_form_cbec0a84
  g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409 -->|recovery_route: Restart invalidates signed cookies and in-memory lockout| g_rv_riverview_v2_workspace_shell_restart_preview_b905f3f1
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Change appearance or sidebar layout| g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d
  g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d -->|Light, Dark, or System selection| g_rv_riverview_v2_workspace_shell_apply_theme_81b77d1d
  g_rv_riverview_v2_workspace_shell_apply_theme_81b77d1d -->|Preference survives reload; system follows OS preference| g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d
  g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d -->|Cycle either sidebar without changing the other| g_rv_riverview_v2_workspace_shell_cycle_sidebars_3ade16cc
  g_rv_riverview_v2_workspace_shell_cycle_sidebars_3ade16cc -->|Hidden state exposes a keyboard-accessible restore button| g_rv_riverview_v2_workspace_shell_restore_sidebars_f1b4862e
  g_rv_riverview_v2_workspace_shell_restore_sidebars_f1b4862e --> g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d
  g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d -->|User requests a V2-specific local ZIP| g_rv_riverview_v2_workspace_shell_snapshot_click_c7b14d94
  g_rv_riverview_v2_workspace_shell_snapshot_click_c7b14d94 --> g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b
  g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b -->|Allowlisted state is captured in memory| g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec
  g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b -->|diagnostic_branch: State capture or hashing fails| g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13
  g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec -->|Members fit the 2 MiB hard bound| g_rv_riverview_v2_workspace_shell_snapshot_download_2aeb1eaf
  g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec -->|diagnostic_branch: Package exceeds the hard bound| g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13
  g_rv_riverview_v2_workspace_shell_snapshot_download_2aeb1eaf -->|verification: Chrome ZIP contents match selected view and hashes| g_rv_riverview_v2_workspace_shell_snapshot_verify_0d5c9c66
  g_rv_riverview_v2_workspace_shell_snapshot_verify_0d5c9c66 --> g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d
  g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13 -->|recovery_route: Retry locally; no upload or service recovery is needed| g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d
  g_rv_riverview_v2_workspace_shell_integration_unavailable_166ea227 -->|No authorized V2 Comms5 event feed is connected| g_rv_riverview_v2_workspace_shell_comms5_unverified_fbb092d5
  g_rv_riverview_v2_workspace_shell_comms5_unverified_fbb092d5 -->|Snapshot includes status and null counts only; no messages, credentials, or fabricated zeros| g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b
  g_rv_riverview_v2_workspace_shell_open_v2_route_83acf28c --> g_rv_riverview_v2_workspace_shell_serve_v2_static_245d797e
  g_rv_riverview_v2_workspace_shell_serve_v2_static_245d797e --> g_rv_riverview_v2_workspace_shell_dashboard_session_62b93d74
  g_rv_riverview_v2_workspace_shell_dashboard_session_62b93d74 -->|Existing Dashboard account cookie is valid| g_rv_riverview_v2_workspace_shell_grace_grants_a8bc5c23
  g_rv_riverview_v2_workspace_shell_dashboard_session_62b93d74 -->|diagnostic_branch: No valid current account session| g_rv_riverview_v2_workspace_shell_dashboard_login_54af0cdd
  g_rv_riverview_v2_workspace_shell_dashboard_login_54af0cdd -->|Dashboard issued secure account and CSRF cookies| g_rv_riverview_v2_workspace_shell_grace_grants_a8bc5c23
  g_rv_riverview_v2_workspace_shell_dashboard_session_62b93d74 -->|diagnostic_branch: Invalid or unavailable account session| g_rv_riverview_v2_workspace_shell_grace_access_denied_ce390666
  g_rv_riverview_v2_workspace_shell_dashboard_login_54af0cdd -->|diagnostic_branch: Login rejected or cross-origin request denied| g_rv_riverview_v2_workspace_shell_grace_access_denied_ce390666
  g_rv_riverview_v2_workspace_shell_grace_grants_a8bc5c23 -->|Exact current read and send grants pass| g_rv_riverview_v2_workspace_shell_grace_load_history_7240fd1d
  g_rv_riverview_v2_workspace_shell_grace_grants_a8bc5c23 -->|diagnostic_branch: Steward role, binding, or exact grant check fails| g_rv_riverview_v2_workspace_shell_grace_access_denied_ce390666
  g_rv_riverview_v2_workspace_shell_grace_load_history_7240fd1d -->|History loaded or no prior conversation exists| g_rv_riverview_v2_workspace_shell_grace_send_message_1990567d
  g_rv_riverview_v2_workspace_shell_grace_send_message_1990567d -->|Server returns conversation and request IDs| g_rv_riverview_v2_workspace_shell_grace_response_state_996c19ef
  g_rv_riverview_v2_workspace_shell_grace_response_state_996c19ef -->|Pending or deferred; resume read-only polling after reload| g_rv_riverview_v2_workspace_shell_grace_response_state_996c19ef
  g_rv_riverview_v2_workspace_shell_grace_response_state_996c19ef -->|verification: Durable assistant event is present in authorized history| g_rv_riverview_v2_workspace_shell_grace_reply_persisted_a711c1c3
  g_rv_riverview_v2_workspace_shell_grace_response_state_996c19ef -->|diagnostic_branch: Grant revoked or service reports a terminal failure| g_rv_riverview_v2_workspace_shell_grace_access_denied_ce390666
  g_rv_riverview_v2_workspace_shell_grace_send_message_1990567d -->|diagnostic_branch: Send result is uncertain; inspect history before any user retry| g_rv_riverview_v2_workspace_shell_grace_recovery_a7678f56
  g_rv_riverview_v2_workspace_shell_grace_access_denied_ce390666 -->|recovery_route: Correct session/service state; never bypass grants or retry send| g_rv_riverview_v2_workspace_shell_grace_recovery_a7678f56
  g_rv_riverview_v2_workspace_shell_grace_recovery_a7678f56 -->|recovery_route: Resume from authoritative persisted conversation events| g_rv_riverview_v2_workspace_shell_grace_load_history_7240fd1d
  g_rv_riverview_v2_workspace_shell_grace_reply_persisted_a711c1c3 -->|verification: Reload re-reads the same durable event IDs and timestamps| g_rv_riverview_v2_workspace_shell_grace_load_history_7240fd1d
  g_rv_riverview_v2_workspace_shell_grace_chat_handoff_29224207 -->|documentation: Superseded by same-origin V2 route| g_rv_riverview_v2_workspace_shell_open_v2_route_83acf28c
  g_rv_riverview_v2_workspace_shell_integration_unavailable_166ea227 -->|documentation: Historical blocker resolved by Steward GO| g_rv_riverview_v2_workspace_shell_open_v2_route_83acf28c
  g_rv_riverview_v2_workspace_shell_open_v2_route_83acf28c -->|Grace API is integrated; Comms5 event ledger remains unavailable| g_rv_riverview_v2_workspace_shell_comms5_unverified_fbb092d5
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Select a resident from Overview or Residents| g_rv_riverview_v2_workspace_shell_route_resident_selection_89cc4007
  g_rv_riverview_v2_workspace_shell_route_resident_selection_89cc4007 -->|Grace selected| g_rv_riverview_v2_workspace_shell_render_grace_center_9f9b903c
  g_rv_riverview_v2_workspace_shell_route_resident_selection_89cc4007 -->|Synthetic resident selected; retain fixture-only directory| g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409
  g_rv_riverview_v2_workspace_shell_render_grace_center_9f9b903c -->|Existing authenticated conversation client checks Dashboard session| g_rv_riverview_v2_workspace_shell_dashboard_session_62b93d74
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Overview or fixture view selected| g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Select Communications Activity| g_rv_riverview_v2_workspace_shell_communications_view_51b400cb
  g_rv_riverview_v2_workspace_shell_communications_view_51b400cb -->|Render current source configuration| g_rv_riverview_v2_workspace_shell_communications_source_check_c3cffc2d
  g_rv_riverview_v2_workspace_shell_communications_source_check_c3cffc2d -->|diagnostic_branch: No authorized read-only activity feed is configured| g_rv_riverview_v2_workspace_shell_communications_unverified_50cc0073
  g_rv_riverview_v2_workspace_shell_communications_unverified_50cc0073 -->|User requests a local configuration check; no network request is sent| g_rv_riverview_v2_workspace_shell_communications_local_refresh_0f9e83ae
  g_rv_riverview_v2_workspace_shell_communications_local_refresh_0f9e83ae -->|recovery_route: Remain UNVERIFIED and retain unknown counts as unavailable| g_rv_riverview_v2_workspace_shell_communications_unverified_50cc0073
  g_rv_riverview_v2_workspace_shell_communications_unverified_50cc0073 -->|Snapshot records safe status and null counters only| g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Select Hardware & AI resources| g_rv_riverview_v2_workspace_shell_resource_monitor_view_55ba762e
  g_rv_riverview_v2_workspace_shell_resource_monitor_view_55ba762e -->|First view or explicit refresh on LAN HTTPS| g_rv_riverview_v2_workspace_shell_resource_dashboard_auth_60501e27
  g_rv_riverview_v2_workspace_shell_resource_dashboard_auth_60501e27 -->|Existing account session is authenticated| g_rv_riverview_v2_workspace_shell_resource_dashboard_status_e9c526f3
  g_rv_riverview_v2_workspace_shell_resource_dashboard_auth_60501e27 -->|diagnostic_branch: Session absent or local fixture origin; do not call protected API| g_rv_riverview_v2_workspace_shell_resource_unavailable_state_5ec2a928
  g_rv_riverview_v2_workspace_shell_resource_dashboard_status_e9c526f3 -->|Validate status-v1 schema and retain allowed timestamped aggregates| g_rv_riverview_v2_workspace_shell_resource_operational_projection_57d5cc51
  g_rv_riverview_v2_workspace_shell_resource_dashboard_status_e9c526f3 -->|Dashboard status has no host GPU or inference queue fields| g_rv_riverview_v2_workspace_shell_resource_unavailable_metrics_cb5fbbef
  g_rv_riverview_v2_workspace_shell_resource_unavailable_metrics_cb5fbbef -->|diagnostic_branch: No approved timestamped resource feed; values remain unavailable| g_rv_riverview_v2_workspace_shell_resource_unavailable_state_5ec2a928
  g_rv_riverview_v2_workspace_shell_resource_monitor_view_55ba762e -->|Use local search/filter/details or explicit refresh| g_rv_riverview_v2_workspace_shell_resource_filter_refresh_3d743915
  g_rv_riverview_v2_workspace_shell_resource_operational_projection_57d5cc51 -->|Snapshot captures source metadata only, not counts or metric values| g_rv_riverview_v2_workspace_shell_resource_snapshot_redaction_41c4cee2
  g_rv_riverview_v2_workspace_shell_resource_unavailable_state_5ec2a928 -->|documentation: Record the future read-only integration seam and blocker| g_rv_riverview_v2_workspace_shell_resource_telemetry_contract_c56ce823
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

The flow covers both the fixture-only preview and the integrated LAN HTTPS `/v2/` route. The HTTPS path inherits Nginx's LAN, Host, Origin and TLS controls, then uses Dashboard-owned account sessions, CSRF, resident binding, exact grants and durable events for Grace chat. Uncertain sends recover by reading history/status; they are never automatically repeated. See the [component specification](RIVERVIEW_V2_WORKSPACE_SHELL.md) and [recovery cookbook](RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md).

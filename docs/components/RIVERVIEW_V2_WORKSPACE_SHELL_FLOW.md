<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL_FLOW.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL · generated from canonical JSON
File Revision: 1.0.13
Purpose: Show normal, decision, failure, and recovery paths for loopback and authenticated LAN preview
Authority: Presentation-only process flow; edit canonical JSON graph only
Changed: 2026-10-20 UTC | RV-WEB-V2-LAN-PREVIEW-001 | Extend generated process view for authenticated LAN access
Changed: 2026-10-20 UTC | RV-WEB-SNAPSHOT-V1-V2-FINAL-001 | Regenerate flow for current V2 handoff/diagnostics and archive integration
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell preview flow

**Task:** `RV-WEB-V2-SHELL-001` · **Component:** `RIVERVIEW-V2-WORKSPACE-SHELL`
**Source:** canonical JSON `process_graphs/riverview-v2/workspace-shell.json`; Mermaid below is generated.

```mermaid
flowchart LR
  subgraph g_rv_riverview_v2_workspace_shell["RIVERVIEW-V2-WORKSPACE-SHELL / local-static-preview"]
    g_rv_riverview_v2_workspace_shell_open_preview_624fa602(["Start loopback or authenticated LAN preview"])
    g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e["Apply Host, client subnet, and password session checks before serving assets"]
    g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409["Render clearly labeled local preview fixtures"]
    g_rv_riverview_v2_workspace_shell_choose_view_161dc67b{"Choose shell view or resident"}
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
    g_rv_riverview_v2_workspace_shell_integration_unavailable_166ea227["Keep V2 chat disconnected and expose the authenticated Dashboard handoff plus unverified Comms5 state"]
    g_rv_riverview_v2_workspace_shell_snapshot_click_c7b14d94(["Click Snapshot in the active V2 view"])
    g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b["Collect allowlisted V2 view, fixture context, browser state, and redacted integration diagnostics"]
    g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec["Build bounded versioned package and manifest; integrated mode uses the shared archive contract"]
    g_rv_riverview_v2_workspace_shell_snapshot_download_2aeb1eaf["Integrated mode archives the same ZIP then downloads it; standalone mode downloads locally only"]
    g_rv_riverview_v2_workspace_shell_snapshot_verify_0d5c9c66["Inspect ZIP members and hashes against active V2 state"]
    g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13[["Show local capture or package-bound failure without upload"]]
    g_rv_riverview_v2_workspace_shell_snapshot_archive_2754d1e2["POST same-origin ZIP with dashboard session and CSRF; shared Steward endpoint validates and archives"]
    g_rv_riverview_v2_workspace_shell_snapshot_local_fallback_5782198a["Retain local ZIP download when archive request fails"]
    g_rv_riverview_v2_workspace_shell_grace_chat_handoff_29224207["Open the deployed authenticated V1 Grace chat; do not transfer credentials or history across origins"]
    g_rv_riverview_v2_workspace_shell_comms5_unverified_fbb092d5["Keep Comms5 send/receive counts and inspectable messages UNVERIFIED when no authorized event feed exists"]
    g_rv_riverview_v2_workspace_shell_manual_image_open_94fa6aaf(["Open Manual Image Generation from V2 navigation"])
    g_rv_riverview_v2_workspace_shell_manual_image_auth_980cfa84{"Require Dashboard account cookie, operator or Steward role, and CSRF for submission"}
    g_rv_riverview_v2_workspace_shell_manual_image_denied_8b33063e[["Reject missing account session, insufficient role, or invalid CSRF"]]
    g_rv_riverview_v2_workspace_shell_manual_image_catalog_e52597f6["Discover workflow definitions and parameter bindings from the registered runtime catalog"]
    g_rv_riverview_v2_workspace_shell_manual_image_validate_666b6204{"Validate UUID, workflow binding, and parameters before persisting the request"}
    g_rv_riverview_v2_workspace_shell_manual_image_submit_5157edc9["Persist idempotent manual provenance and invoke the existing bounded ComfyUIAction"]
    g_rv_riverview_v2_workspace_shell_manual_image_progress_6829a78f["Persist execution status and progress from the ComfyUI worker"]
    g_rv_riverview_v2_workspace_shell_manual_image_interrupted_d3c8d138["Resume durable requests through the existing ComfyUI action journal after Dashboard restart"]
    g_rv_riverview_v2_workspace_shell_manual_image_verify_f0fc10a3["Verify exact ComfyUI history prompt and extra_data assignment/template identity, then independently validate PNG bytes, dimensions, ownership and digest"]
    g_rv_riverview_v2_workspace_shell_manual_image_download_63653eba["Serve owner-scoped preview and download through the authenticated artifact route"]
    g_rv_riverview_v2_workspace_shell_manual_image_failed_4974021e[["Persist worker, timeout, output, or verification failure without exposing unverified bytes"]]
    g_rv_riverview_v2_workspace_shell_manual_image_gpu_disabled_fefa7853{"Keep per-request GPU selection disabled while allocator or reservation identity is unavailable"}
  end
  g_rv_riverview_v2_workspace_shell_open_preview_624fa602 --> g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e
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
  g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d -->|V2 has no shared Dashboard identity; show the separate secure handoff| g_rv_riverview_v2_workspace_shell_integration_unavailable_166ea227
  g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d -->|User requests a V2-specific local ZIP| g_rv_riverview_v2_workspace_shell_snapshot_click_c7b14d94
  g_rv_riverview_v2_workspace_shell_snapshot_click_c7b14d94 --> g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b
  g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b -->|Allowlisted state is captured in memory| g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec
  g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b -->|diagnostic_branch: State capture or hashing fails| g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13
  g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec -->|diagnostic_branch: Package exceeds the hard bound| g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13
  g_rv_riverview_v2_workspace_shell_snapshot_download_2aeb1eaf -->|verification: Chrome ZIP contents match selected view and hashes| g_rv_riverview_v2_workspace_shell_snapshot_verify_0d5c9c66
  g_rv_riverview_v2_workspace_shell_snapshot_verify_0d5c9c66 --> g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d
  g_rv_riverview_v2_workspace_shell_snapshot_failure_3be3aa13 -->|recovery_route: Retry locally; no upload or service recovery is needed| g_rv_riverview_v2_workspace_shell_choose_presentation_7aa0553d
  g_rv_riverview_v2_workspace_shell_snapshot_manifest_bae7acec --> g_rv_riverview_v2_workspace_shell_snapshot_archive_2754d1e2
  g_rv_riverview_v2_workspace_shell_snapshot_archive_2754d1e2 --> g_rv_riverview_v2_workspace_shell_snapshot_download_2aeb1eaf
  g_rv_riverview_v2_workspace_shell_snapshot_archive_2754d1e2 -->|diagnostic_branch| g_rv_riverview_v2_workspace_shell_snapshot_local_fallback_5782198a
  g_rv_riverview_v2_workspace_shell_snapshot_local_fallback_5782198a -->|recovery_route| g_rv_riverview_v2_workspace_shell_snapshot_download_2aeb1eaf
  g_rv_riverview_v2_workspace_shell_integration_unavailable_166ea227 -->|Steward opens authenticated V1 Dashboard Grace chat in a separate tab| g_rv_riverview_v2_workspace_shell_grace_chat_handoff_29224207
  g_rv_riverview_v2_workspace_shell_integration_unavailable_166ea227 -->|No authorized V2 Comms5 event feed is connected| g_rv_riverview_v2_workspace_shell_comms5_unverified_fbb092d5
  g_rv_riverview_v2_workspace_shell_comms5_unverified_fbb092d5 -->|Snapshot includes status and null counts only; no messages, credentials, or fabricated zeros| g_rv_riverview_v2_workspace_shell_snapshot_capture_d124e47b
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Select Image generation| g_rv_riverview_v2_workspace_shell_manual_image_open_94fa6aaf
  g_rv_riverview_v2_workspace_shell_manual_image_open_94fa6aaf --> g_rv_riverview_v2_workspace_shell_manual_image_auth_980cfa84
  g_rv_riverview_v2_workspace_shell_manual_image_auth_980cfa84 -->|diagnostic_branch: Cookie missing, role denied, or CSRF invalid| g_rv_riverview_v2_workspace_shell_manual_image_denied_8b33063e
  g_rv_riverview_v2_workspace_shell_manual_image_denied_8b33063e -->|recovery_route: Sign in through the Dashboard and retry| g_rv_riverview_v2_workspace_shell_manual_image_open_94fa6aaf
  g_rv_riverview_v2_workspace_shell_manual_image_auth_980cfa84 -->|Authorized operator or Steward session| g_rv_riverview_v2_workspace_shell_manual_image_catalog_e52597f6
  g_rv_riverview_v2_workspace_shell_manual_image_catalog_e52597f6 -->|Display configured worker; GPU selection remains unavailable| g_rv_riverview_v2_workspace_shell_manual_image_gpu_disabled_fefa7853
  g_rv_riverview_v2_workspace_shell_manual_image_gpu_disabled_fefa7853 --> g_rv_riverview_v2_workspace_shell_manual_image_validate_666b6204
  g_rv_riverview_v2_workspace_shell_manual_image_validate_666b6204 -->|Inputs match the discovered workflow schema| g_rv_riverview_v2_workspace_shell_manual_image_submit_5157edc9
  g_rv_riverview_v2_workspace_shell_manual_image_validate_666b6204 -->|diagnostic_branch: Unknown workflow or invalid parameter| g_rv_riverview_v2_workspace_shell_manual_image_failed_4974021e
  g_rv_riverview_v2_workspace_shell_manual_image_submit_5157edc9 --> g_rv_riverview_v2_workspace_shell_manual_image_progress_6829a78f
  g_rv_riverview_v2_workspace_shell_manual_image_submit_5157edc9 -->|diagnostic_branch: Dashboard interruption or indeterminate submit| g_rv_riverview_v2_workspace_shell_manual_image_interrupted_d3c8d138
  g_rv_riverview_v2_workspace_shell_manual_image_interrupted_d3c8d138 -->|recovery_route: Existing ComfyUI journal resumes the same request identity| g_rv_riverview_v2_workspace_shell_manual_image_progress_6829a78f
  g_rv_riverview_v2_workspace_shell_manual_image_progress_6829a78f -->|ComfyUI reports output complete| g_rv_riverview_v2_workspace_shell_manual_image_verify_f0fc10a3
  g_rv_riverview_v2_workspace_shell_manual_image_progress_6829a78f -->|diagnostic_branch: Worker error, conflict, or timeout| g_rv_riverview_v2_workspace_shell_manual_image_failed_4974021e
  g_rv_riverview_v2_workspace_shell_manual_image_verify_f0fc10a3 -->|verification: Independent verifier accepts valid PNG| g_rv_riverview_v2_workspace_shell_manual_image_download_63653eba
  g_rv_riverview_v2_workspace_shell_manual_image_verify_f0fc10a3 -->|diagnostic_branch: Output identity, bytes, or media validation fails| g_rv_riverview_v2_workspace_shell_manual_image_failed_4974021e
  g_rv_riverview_v2_workspace_shell_manual_image_failed_4974021e -->|recovery_route: Review history, then submit a new request ID| g_rv_riverview_v2_workspace_shell_manual_image_open_94fa6aaf
  g_rv_riverview_v2_workspace_shell_manual_image_download_63653eba -->|Return to V2 workspace| g_rv_riverview_v2_workspace_shell_choose_view_161dc67b
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

The process describes the fixture-only shell in loopback or password-protected trusted-LAN mode. The LAN mode requires a local salted password hash, verifies the client subnet and Host, and rejects non-read-only methods; HTTP credentials are confined to trusted LAN use. Restarting revokes sessions and resets in-memory selection/lockout state. See the [component specification](RIVERVIEW_V2_WORKSPACE_SHELL.md) and [recovery cookbook](RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md).

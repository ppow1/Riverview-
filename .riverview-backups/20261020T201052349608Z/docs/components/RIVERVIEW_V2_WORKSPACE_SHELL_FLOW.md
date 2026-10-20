<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL_FLOW.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL · generated from canonical JSON
File Revision: 1.0.3
Purpose: Show normal, decision, failure, and recovery paths for loopback and authenticated LAN preview
Authority: Presentation-only process flow; edit canonical JSON graph only
Changed: 2026-10-20 UTC | RV-WEB-V2-LAN-PREVIEW-001 | Extend generated process view for authenticated LAN access
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
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

The process describes the fixture-only shell in loopback or password-protected trusted-LAN mode. The LAN mode requires a local salted password hash, verifies the client subnet and Host, and rejects non-read-only methods; HTTP credentials are confined to trusted LAN use. Restarting revokes sessions and resets in-memory selection/lockout state. See the [component specification](RIVERVIEW_V2_WORKSPACE_SHELL.md) and [recovery cookbook](RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md).

<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL_FLOW.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL · generated from canonical JSON
File Revision: 1.0.1
Purpose: Show normal, decision, failure, and recovery paths for the local preview
Authority: Presentation-only process flow; edit canonical JSON graph only
Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Initial generated process view
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell preview flow

**Task:** `RV-WEB-V2-SHELL-001` · **Component:** `RIVERVIEW-V2-WORKSPACE-SHELL`  
**Source:** canonical JSON `process_graphs/riverview-v2/workspace-shell.json`; Mermaid below is generated.

```mermaid
flowchart LR
  subgraph g_rv_riverview_v2_workspace_shell["RIVERVIEW-V2-WORKSPACE-SHELL / local-static-preview"]
    g_rv_riverview_v2_workspace_shell_open_preview_624fa602(["Start local loopback preview"])
    g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e["Serve same-origin static shell with network connections denied"]
    g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409["Render clearly labeled local preview fixtures"]
    g_rv_riverview_v2_workspace_shell_choose_view_161dc67b{"Choose shell view or resident"}
    g_rv_riverview_v2_workspace_shell_retain_context_f40171d8["Retain selected resident in browser memory across views"]
    g_rv_riverview_v2_workspace_shell_unsafe_method_4b803134[["Reject mutating preview methods and out-of-root paths"]]
    g_rv_riverview_v2_workspace_shell_restart_preview_b905f3f1["Restart local preview and reload; state resets to default"]
    g_rv_riverview_v2_workspace_shell_stop_preview_9aec5773(["Stop preview process without affecting V1"])
  end
  g_rv_riverview_v2_workspace_shell_open_preview_624fa602 --> g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e
  g_rv_riverview_v2_workspace_shell_serve_static_9f085d0e --> g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409
  g_rv_riverview_v2_workspace_shell_render_fixtures_e2ce6409 --> g_rv_riverview_v2_workspace_shell_choose_view_161dc67b
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Select resident; context remains across views| g_rv_riverview_v2_workspace_shell_retain_context_f40171d8
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|diagnostic_branch: Unsafe method or path is attempted| g_rv_riverview_v2_workspace_shell_unsafe_method_4b803134
  g_rv_riverview_v2_workspace_shell_unsafe_method_4b803134 -->|recovery_route: Resume by restarting local preview if needed| g_rv_riverview_v2_workspace_shell_restart_preview_b905f3f1
  g_rv_riverview_v2_workspace_shell_retain_context_f40171d8 -->|Navigate while selected resident remains in memory| g_rv_riverview_v2_workspace_shell_choose_view_161dc67b
  g_rv_riverview_v2_workspace_shell_choose_view_161dc67b -->|Stop foreground preview| g_rv_riverview_v2_workspace_shell_stop_preview_9aec5773
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

The process describes the local fixture-only shell. Unsafe methods and paths are rejected; restarting the preview resets only in-memory preview state. See the [component specification](RIVERVIEW_V2_WORKSPACE_SHELL.md) and [recovery cookbook](RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md).

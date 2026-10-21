<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.0
Purpose: Diagnose and recover the local V2 shell preview
Authority: Read-only local diagnostics; no production recovery action
Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Initial V2 shell recovery guide
History: Git and revision/backup manifest
-->
# V2 workspace shell preview: troubleshooting and recovery

This guide applies only to the local fixture preview in `RIVERVIEW-V2-WORKSPACE-SHELL.md`. It does not diagnose or restart the V1 Dashboard.

## Start, stop, and resume

Start from the worktree root:

```sh
python3 scripts/serve_v2_workspace_preview.py --host 127.0.0.1 --port 8877
```

Expected output identifies `http://127.0.0.1:8877/` and says loopback only. Open that URL on the same machine. To use a browser on a separate workstation, run an SSH local port forward to Camrui; retain the loopback listener on Camrui. Stop with Ctrl-C. Restart with the same command; all selection state is intentionally in memory and resets to Grace.

## Symptoms and diagnostics

| Symptom | Read-only check | Expected output | Recovery |
| --- | --- | --- | --- |
| Address already in use | `ss -ltnp '( sport = :8877 )'` | No listener before starting, or identify the existing local preview process | Stop only the preview process owned by this checkout, or choose another loopback port. Do not stop unrelated services. |
| Browser cannot connect | `curl -i http://127.0.0.1:8877/` | HTTP 200 and HTML | Confirm the foreground server is running and URL/port match. Restart the preview process only. |
| Page loads without content | `curl -i http://127.0.0.1:8877/assets/fixtures.js` and `/assets/workspace.js` | HTTP 200; browser console has no parse errors | Refresh, then inspect local checkout files. No server-side state needs recovery. |
| A method is rejected | `curl -i -X POST http://127.0.0.1:8877/` | HTTP 405 `preview is read-only` | Expected safety behavior; use the visible read-only preview. |
| A file path is missing | `curl -i http://127.0.0.1:8877/../...` | 404 or safely rejected path | Expected boundary. Use only the root and `/assets/*` paths. |
| Mobile menu does not close automatically | Tap the menu button again | Navigation rail returns off-canvas | This preview has no router or automatic navigation state. |

No SQL, credentials, migrations, service manager, Nginx, firewall, or production API is involved. A preview failure has no production recovery step. Resume by restarting the local command and reloading the browser.

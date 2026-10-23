<!--
Changed: 2026-10-20 UTC | RV-WEB-SNAPSHOT-V1-V2-INTEGRATION-001 | Add integrated Snapshot authentication, archive and fallback troubleshooting.
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.7
Purpose: Diagnose and recover the local or password-protected LAN V2 shell preview
Authority: Read-only local diagnostics; no production recovery action
Changed: 2026-10-20 UTC | RV-WEB-V2-SNAPSHOT-001 | Add snapshot download validation, limits and recovery
Changed: 2026-10-20 UTC | RV-WEB-SNAPSHOT-V1-V2-FINAL-001 | Document integrated fallback verification and current V2 diagnostic boundaries
History: Git and revision/backup manifest
-->
# V2 workspace shell preview: troubleshooting and recovery

This guide applies only to the fixture preview in `RIVERVIEW-V2-WORKSPACE-SHELL.md`. It does not diagnose or restart the V1 Dashboard. LAN mode is HTTP and must stay on the trusted Riverview LAN; it is not safe over public Wi-Fi or an untrusted network.

## Start, stop, and resume

The default loopback preview is:

```sh
python3 scripts/serve_v2_workspace_preview.py --host 127.0.0.1 --port 8877
```

Expected output identifies `http://127.0.0.1:8877/` and says loopback only. Open that URL on the checkout host. Stop with Ctrl-C. Restart with the same command; selection state is intentionally in memory and resets to Grace.

### Start trusted-LAN access

Confirm Camrui has `192.168.1.155/24` and the Windows development PC is on `192.168.1.0/24`. Do not widen the subnet to make an unreachable client work.

The Steward chooses the password on Camrui through a hidden prompt:

```sh
python3 scripts/setup_v2_workspace_preview_auth.py
```

Expected output gives the hash-file path and confirms the plaintext was not saved. Do not display or publish this file. Check metadata only:

```sh
stat -c '%a %U:%G %n' /home/admin1/.config/riverview/v2-preview-auth.json
```

Expected file mode is `600`, owned by the preview operator. Start the foreground server on the explicit LAN interface:

```sh
python3 scripts/serve_v2_workspace_preview.py --host 192.168.1.155 --port 8877 --trusted-network 192.168.1.0/24 --auth-file /home/admin1/.config/riverview/v2-preview-auth.json
```

Expected output says `password protected` and `Trusted clients: 192.168.1.0/24`. The listener must be `192.168.1.155:8877`, never `0.0.0.0:8877`. It accepts only the configured subnet and expected Host. From Windows Chrome on that LAN, open `http://192.168.1.155:8877/` and enter the chosen password. The authenticated cookie lasts eight hours. Five failed attempts from one address in 15 minutes return 429 with Retry-After for 15 minutes. Restarting the process revokes cookies and clears temporary lockout state.

The login page warns that HTTP does not encrypt the password or cookie in transit. Do not enter the password on an untrusted network. HTTPS reuse requires a V2 route in production Nginx and separate authorization; no such change is part of this preview increment.

## Symptoms and diagnostics

| Symptom | Read-only check | Expected output | Recovery |
| --- | --- | --- | --- |
| Address already in use | `ss -ltnp '( sport = :8877 )'` | Identify the exact PID and bind address | Stop only the preview process owned by this checkout. Do not stop unrelated services. |
| Windows cannot connect | On Camrui: `ip -4 -o addr show dev eno1`; `ss -ltnp '( sport = :8877 )'`; `curl -sS -o /dev/null -w '%{http_code}\n' http://192.168.1.155:8877/` | Interface `192.168.1.155/24`; listener `192.168.1.155:8877`; login page HTTP 200 | Confirm Windows is on `192.168.1.0/24` and the numeric URL is used. Do not change firewall/Nginx or widen the subnet without authorization. |
| Login page appears but submit returns 403 `login origin rejected` | In browser developer tools, inspect the POST Origin; do not capture password/form contents | Same-origin `http://192.168.1.155:8877` is accepted; `Origin: null` or absent must have a fresh hidden CSRF token; foreign scheme/host/port remains rejected | Reload the login page to receive a fresh five-minute one-use token. Never disable Host or Origin checks. The token is bound to the client IP and consumed once. |
| Login page appears but asset gets 401 | Open the root URL and enter the password again | Static shell loads after successful form POST | Restart invalidates cookies; log in again. A cleartext secret is never needed in a URL. |
| Login submit returns 403 `login CSRF token rejected` | Reload `/`; ensure the submitted form includes its hidden `csrf_token`; do not disclose it in diagnostics | Each login form has one unpredictable, five-minute token; a token cannot be replayed or used from a different client IP | Submit the newly loaded form. Do not fabricate a token or weaken origin validation. Restarting clears all tokens. |
| Password rejected | Check `stat -c '%a %U:%G %n' /home/admin1/.config/riverview/v2-preview-auth.json` only | Mode 600, owner is preview operator; never display contents | Steward chooses a new password through setup prompt with `--replace`, then restart only the preview. |
| Login temporarily limited | Browser response status 429; inspect no request logs | `Retry-After` header, up to 900 seconds | Wait the indicated interval. Do not restart to bypass the lockout. |
| Client denied with 403 | Confirm client IP is inside the configured /24; verify browser used `192.168.1.155:8877` Host | Trusted LAN and expected Host required | Correct the client network or URL. Any ACL change needs reviewed scope; do not allow all interfaces. |
| Host rejected with 400 | Inspect browser address bar | Host header matches the explicit IP and port | Use the numeric URL, not an unconfigured alias. |
| A method is rejected | `curl -i -X PUT http://127.0.0.1:8877/` on loopback preview | HTTP 405 `preview is read-only` | Expected safety behavior; only the password form accepts POST in LAN-auth mode. |
| A file path is missing | `curl -i http://127.0.0.1:8877/../...` | 404 or safely rejected path | Expected boundary. Use only the root and `/assets/*` paths. |
| Theme selection does not persist | Read `localStorage.getItem('rv.v2.theme')` in the browser console | `light`, `dark`, or `system`; an unavailable storage API falls back to System for that page | Choose the theme again; no account data is stored in this preference. |
| Theme does not follow OS changes | Inspect the Theme selector | `System` is selected; explicit Light/Dark does not follow OS changes | Select `System`; while System is selected, the page follows `prefers-color-scheme`. |
| Sidebar is compact or missing | Activate the corresponding sidebar state button; inspect `data-left-state` / `data-right-state` on `.app-shell` | `expanded`, `compact`, or `hidden`; each side changes independently | Use the small floating restore button when hidden. Focus it with Tab and press Enter/Space. |
| Tooltip is not visible | Tab to the control or hover it; inspect `aria-description` | Description appears on keyboard focus/hover and is available as an accessible description | Use the visible control label or its accessible name; browser zoom/reduced motion are supported. |
| Snapshot does not download | Click Snapshot and read the status below it | A ZIP is downloaded and the status gives its byte size; no server upload is attempted | Retry after ensuring downloads are allowed. If the status reports a bound/hash error, retain the visible message and use the read-only check below; do not treat it as an archive upload. |
| Snapshot ZIP is invalid or does not match the visible view | Use `python3 -m zipfile -t <downloaded.zip>` and inspect `workspace-state.json`, `rendered-view.txt`, and `manifest.json` | Four members; each non-manifest member has a matching SHA-256 and size in the manifest; route/view/selected resident/theme/sidebar match the browser at click time | Preserve the ZIP and report its SHA-256 and browser version. Retry after verifying the active route. The ZIP has a 2 MiB hard limit and includes no screenshot, server logs, live data, cookies, or credentials. |
| Snapshot hash check fails in browser | Inspect status only; do not copy browser storage or credentials into diagnostics | Snapshot either completes with the local ZIP size or reports it could not be created; no server write occurred | Retry once. If it persists, save sanitized browser console error metadata and use the Chrome acceptance runner. No service restart is relevant. |
| Chat composer is disabled | Inspect the New conversation control and ChatGPT link | V2 has no resident conversation API; ChatGPT opens an unrelated external client | No resident context is transferred. Enable only after a reviewed authenticated conversation contract exists. |
| Mobile menu does not close automatically | Tap the menu button again | Navigation rail returns off-canvas | This preview has no router or automatic navigation state. |

No SQL, migrations, service manager, Nginx, firewall, or production API is involved. The password hash is a local credential file and is never copied into Git. A preview failure has no production recovery step.

### Rollback and resume

1. Stop only the foreground preview owned by this worktree with Ctrl-C.
2. Confirm V1 remains active with `systemctl is-active riverview-status-dashboard.service`; expected output is `active`.
3. To resume prior loopback-only behavior, run `python3 scripts/serve_v2_workspace_preview.py --host 127.0.0.1 --port 8877`. No LAN password file is needed.
4. To resume LAN mode, verify the protected hash file metadata, explicit host and subnet, then restart the LAN command. The browser receives a new cookie after login.
5. To rotate the LAN password, Steward runs the local hidden setup prompt with `--replace`; restart V2 to invalidate existing sessions.
6. Never roll back V1 or Nginx for a V2 preview failure.

## Reproducible checkout checks

```sh
python3 -m unittest tests.test_v2_workspace_shell -v
python3 scripts/verify_v2_workspace_browser.py --base-url http://192.168.1.155:8877 --password-prompt
python3 scripts/verify_v2_workspace_snapshot_chrome.py --base-url http://192.168.1.155:8877/ --evidence-dir <evidence-dir> --password-prompt
node scripts/verify_v2_workspace_mobile.cjs --url http://127.0.0.1:8877/
python3 scripts/process_graph.py validate
python3 scripts/process_graph.py check
```

The Firefox utility starts and stops its own local geckodriver. The Chrome utility starts and stops its own headless Chrome profile and uses a 390×844 CSS-pixel emulated viewport. Both connect only to the loopback preview. LAN authentication tests use a disposable random password created in memory and a temporary hash; they never test with the Steward's real password. Required outputs include no browser errors, selected resident retained, `overflow=false`, unauthorized assets 401, successful login redirect 303, lockout 429, invalid Host/Origin and non-LAN rejection, null/absent Origin accepted only with a valid one-use CSRF token, replay/missing-token rejection, and session expiry. Final acceptance also requires Windows Chrome from the actual dev PC. A failed local check is evidence about the preview branch, not a reason to restart V1.

The focused browser checks also exercise all three theme choices, persistence of the chosen display preference, all sidebar states and restoration controls, keyboard descriptions, mobile width, the exact Snapshot label, and a real ZIP whose contents and manifest hashes match selected V2 state. The authenticated V1 Grace handoff is a separate-tab link; Comms5 counts stay UNVERIFIED/null. For integrated `/v2/`, verify the archive receipt and local ZIP have the same SHA-256; test archive failure preserves local download, and local-download failure preserves the confirmed release link. To roll back this integration only, restore the exact pre-change files listed in `.riverview-backups/manifest.jsonl` and redeploy only under the separately approved dashboard procedure. Never touch V1, Nginx, credentials, or production as part of the V2 preview rollback.


## Integrated Snapshot recovery

For the dashboard-integrated shell, navigate to `/v2/` on the dashboard HTTPS origin. If the package fails before archive submission, check the visible status and read-only Network entries for authenticated GET failures to `/api/v1/status` or `/api/v1/snapshot`. Sign in to the dashboard and reload. For an archive 403, reload once to refresh CSRF state and click Snapshot. For GitHub/archive 5xx or network errors, the local ZIP remains the recovery artifact; do not repeatedly click while the first request is pending. A confirmed archive must show the release link, capture ID in its asset filename, and Copy GitHub Link. If local download is blocked, use the confirmed release link. Standalone LAN preview behavior is unchanged and never archives.

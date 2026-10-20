<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.9
Purpose: Diagnose and recover the isolated preview and center-workspace same-origin HTTPS V2 Grace chat
Authority: Read-only diagnostics except the authorized V2 route rollback and Steward-initiated chat
Changed: 2026-10-20 UTC | RV-WEB-V2-GRACE-WORKSPACE-003 | Add center-workspace selection and browser recovery checks
History: Git and revision/backup manifest
-->
# V2 workspace shell preview: troubleshooting and recovery

The first procedures cover the isolated HTTP fixture preview; the integrated HTTPS route and Grace API procedures are separate below. This guide does not restart the V1 Dashboard. The fixture preview uses HTTP and must stay on the trusted Riverview LAN; it is not safe over public Wi-Fi or an untrusted network.

## Integrated V2 LAN route and real Grace chat

The integrated UI is `https://192.168.1.155/v2/`. Nginx serves the versioned static V2 release, while `/api/v1/*` continues to the existing V1 Dashboard at `/`; both paths are HTTPS and share the exact browser origin. The Nginx server's existing `192.168.1.0/24`, Host, Origin, and TLS checks remain in force. The isolated `http://192.168.1.155:8877/` preview remains password-gated but deliberately cannot use Grace's API.

### Read-only route and service checks

Run from Camrui; expected V2 page response is `200`, `Content-Type: text/html`, `Cache-Control: no-store`, and a CSP containing `connect-src 'self'`. V1 root must also return `200` and its systemd unit must remain active.

```sh
curl -sS -D /tmp/rv-v2-headers.txt -o /dev/null -w 'V2 HTTP %{http_code}\n' https://192.168.1.155/v2/
curl -sS -o /dev/null -w 'V1 HTTP %{http_code}\n' https://192.168.1.155/
systemctl is-active riverview-status-dashboard.service
sudo nginx -t
```

Do not use `curl -k` to conceal certificate failures. Without credentials, `GET /api/v1/resident/conversations` must return `401`; a state-changing conversation-session request without account cookie/CSRF must also return `401`. The V2 page itself may be visible to LAN clients, as is V1's login page, but conversation content and send authority require Dashboard authentication and exact grants.

### Open and verify the Grace center workspace

1. In V2, select **Residents** in the left navigation. Select the Grace row; the page title becomes **Grace conversation** and the chat card appears in the center content column. The right sidebar contains only supporting resident/integration context.
2. Select **Overview** to return to the overview. Selecting a synthetic resident keeps the fixture directory visible and must not display a Grace composer. Reopen Grace from Residents.
3. At a desktop viewport, the conversation card should occupy the available center-column width and its history should scroll inside the card. At phone width (390 CSS px), no horizontal document overflow should appear; the history remains scrollable and the composer stays visible below it.
4. The HTTP loopback/LAN fixture preview intentionally says HTTPS is required and does not connect to Dashboard; the sign-in, conversation, durable history and sending remain available only through same-origin HTTPS `/v2/` with an authorized Dashboard session.
5. Snapshot records the selected `grace-conversation` view and connection state, but never conversation content. A not-connected HTTP fixture snapshot is expected to report Grace chat as unavailable.

### Sign-in, history, and message lifecycle

1. Open the HTTPS `/v2/` route in Chrome. The preview-only HTTP route reports that HTTPS is required and does not call the Dashboard API.
2. If no Dashboard session exists, enter the Steward's approved Dashboard email/password in the V2 sign-in form. The browser submits directly over HTTPS to same-origin `POST /api/v1/auth/session`; the password is cleared after the request. Do not use the separate V2 preview password here.
3. V2 checks `GET /api/v1/auth/session`, then calls `POST /api/v1/resident/conversation-session`. Dashboard verifies the Steward role and current `resident.conversation.read` and `.send` grants. Each protected request rechecks account cookie, CSRF on writes, conversation cookie, resident binding, and grants. A `403 resident_conversation_not_authorized` is an authorization denial; do not retry under another identity or provision a new credential.
4. V2 loads `GET /api/v1/resident/conversations` and selected `GET /api/v1/resident/conversations/{id}`. Dashboard's durable append-only events are authoritative. Refresh/reload re-reads them; browser storage contains only selected conversation ID, never transcript text.
5. A send uses a one-time UUID `client_message_id` and `POST /api/v1/resident/conversations/stream`. A returned `request_id` and `conversation_id` mean request acceptance, not completed reply. V2 polls read-only `GET /api/v1/resident/conversations/{id}/responses/{request_id}` and refreshes durable history at terminal state. User/assistant entries display persisted event sequence and timestamp.
6. If the send result is uncertain, refresh history and inspect the persisted user event/request status before retrying. The UI never automatically resends. `pending`/`deferred` are not completion; `failed`/`interrupted` remain visible. After reload, V2 resumes read-only status checks from persisted pending events.
7. Snapshot includes only observed chat connection/history-loaded state and a bounded event count. It excludes identity, conversation/message IDs, text, credentials, and error payloads. Comms5 remains `UNVERIFIED` with unknown counters as `null`.

### Error table and resume points

| Symptom / response | Read-only diagnostic | Meaning | Safe recovery / resume |
| --- | --- | --- | --- |
| `/v2/` returns 404 | `curl -sS -D - -o /dev/null https://192.168.1.155/v2/`; inspect `sudo nginx -T` for V2 include | Static release or route include unavailable | Check release directory and `nginx -t`; if V1 root health changed, restore only this task's Nginx predecessor; resume when `/v2/` has expected headers. |
| V2 says HTTPS is required | Check browser URL | Browser opened HTTP preview at port 8877 | Open `https://192.168.1.155/v2/`; do not enable API calls over the preview origin. |
| Sign-in required / API 401 | `curl -sS -o /dev/null -w '%{http_code}\n' https://192.168.1.155/api/v1/resident/conversations` without credentials | No valid account/conversation session | Sign in through V2; never copy cookies or bearer values. |
| `resident_conversation_not_authorized` / HTTP 403 | Read visible V2 status; Dashboard authorization decision is authoritative | Current account lacks exact grants/binding, or session/CSRF was rejected | Stop sending; sign in once again. If still denied, use normal Steward permission review. Do not bypass the denial. |
| `resident_conversation_unavailable` / HTTP 503 | `systemctl is-active riverview-status-dashboard.service`; `journalctl -u riverview-status-dashboard.service --since '-10 min' --no-pager` | Existing API or dependency unavailable | Do not restart V1 as V2 recovery. Retain request ID, wait for normal service recovery, refresh history, and inspect whether the user event persisted before resuming. |
| Request remains pending | Refresh history; inspect event sequence/status; use the read-only response endpoint | Durable request exists without terminal response evidence | Wait/read status; do not resend. A persisted interrupted state after restart is terminal and needs a new user decision. |
| CSS/JS missing or wrong release | `sha256sum /var/www/riverview-v2-preview/releases/RV-WEB-V2-GRACE-CHAT-002/*`; inspect content type/CSP headers | Release copy or permissions problem | Re-copy from the verified source commit, ensure Nginx can read files, then reload `/v2/`. The route uses `no-store`. |

### Reversible Nginx deployment

The exact site-config predecessor is root-only at `/var/lib/riverview/engineering-backups/RV-WEB-V2-GRACE-CHAT-002/riverview-lan.predecessor`; its SHA-256 and `cmp` result are recorded in acceptance evidence. The source include is `deploy/nginx/riverview-v2.location.conf`; installed copy is `/etc/nginx/snippets/riverview-v2.conf`. Release files are under `/var/www/riverview-v2-preview/releases/RV-WEB-V2-GRACE-CHAT-002/`.

Rollback restores `/etc/nginx/sites-available/riverview-lan` from the protected predecessor, verifies `cmp` and SHA-256, runs `sudo nginx -t`, then `sudo systemctl reload nginx`. This is a graceful Nginx reload; do not restart the V1 Dashboard. The now-inactive include/static release may remain on disk. Verify V1 `/` is still `200`, its service is `active`, and `/v2/` no longer resolves to this integration. If V1 root health fails after reload, rollback immediately.

## Start, stop, and resume

The default loopback preview is:

```sh
python3 scripts/serve_v2_workspace_preview.py --host 127.0.0.1 --port 8877
```

Expected output identifies `http://127.0.0.1:8877/` and says loopback only. Open that URL on the checkout host. Stop with Ctrl-C. Restart with the same command; resident selection is intentionally in memory and defaults to Grace while the active view starts at Overview.

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
| Grace chat cannot send from V2 | Open `https://192.168.1.155/v2/`; inspect the visible state and `GET /api/v1/auth/session` result | The HTTPS V2 route uses the existing Dashboard account cookie, CSRF token, conversation session and exact grants. The HTTP fixture preview remains disconnected. | Sign in through the V2 same-origin form with the authorized Steward account. If the API denies exact grants, stop and use normal permission review. Never copy bearer values or cookies. |
| Comms5 counts or messages appear unavailable | Inspect the Comms5 card and the Snapshot `communication_diagnostics` object | Expected: `status=unverified`, outbound/inbound counts `null`, inspectable messages `false`; unknown is not zero. The Comms5 v5 capability list has no general message ledger operation for V2. | Do not infer counters from the Dashboard event list or unrelated Comms5 operations. Resume only when an independently recorded, authorized Comms5 event projection is available. |
| Grace chat appears in the right sidebar or disappears on navigation | Open Residents, select Grace, then inspect `#workspace-main` and `#right-sidebar` in DevTools | `#grace-chat-root` is inside `#workspace-main`; the right sidebar contains supporting context only | Select Residents then Grace again. If the center panel is missing, verify the served `workspace.js` and `index.html` belong to the same V2 release; do not change API, Nginx or V1 to repair a static UI issue. |
| Mobile Grace workspace overflows horizontally | At 390 CSS px inspect `document.documentElement.scrollWidth` and `innerWidth` | Scroll width is no greater than viewport width; history scrolls internally | Reload the current V2 assets, reset sidebar widths and rerun the Chrome viewport check. Do not modify the global LAN route for a CSS defect. |
| Mobile menu does not close automatically | Tap the menu button again | Navigation rail returns off-canvas | This preview has no router or automatic navigation state. |

The fixture preview uses no SQL, migration, service manager, Nginx, firewall, or production API. The integrated route uses only the authorized `/v2/` Nginx static include and existing Dashboard APIs; it changes no database or service. The preview password hash is local and never copied into Git.

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
node scripts/verify_v2_workspace_mobile.cjs --url http://127.0.0.1:8877/ --width 1440 --height 1000
node scripts/verify_v2_workspace_mobile.cjs --url http://127.0.0.1:8877/ --width 390 --height 844
python3 scripts/process_graph.py validate
python3 scripts/process_graph.py check
```

The Firefox utility starts and stops its own local geckodriver. The Chrome utility starts and stops its own headless Chrome profile and uses a 390×844 CSS-pixel emulated viewport. Both connect only to the loopback preview. LAN authentication tests use a disposable random password created in memory and a temporary hash; they never test with the Steward's real password. Required outputs include no browser errors, selected resident retained, `overflow=false`, unauthorized assets 401, successful login redirect 303, lockout 429, invalid Host/Origin and non-LAN rejection, null/absent Origin accepted only with a valid one-use CSRF token, replay/missing-token rejection, and session expiry. Final acceptance also requires Windows Chrome from the actual dev PC. A failed local check is evidence about the preview branch, not a reason to restart V1.

The focused fixture browser checks exercise theme choices, sidebar states, keyboard descriptions, mobile width, Snapshot, truthful Comms5 `UNVERIFIED` state, and a real ZIP download. The separate Chrome Grace acceptance runner checks one actual durable send, Grace response, and reload; it requires Chrome trust of the LAN Root CA and an authorized Dashboard session. It reports only hashed identifiers and event metadata. To roll back the integrated route, restore the protected Nginx predecessor from `/var/lib/riverview/engineering-backups/RV-WEB-V2-GRACE-CHAT-002/`, verify the recorded SHA-256, run `nginx -t`, and reload Nginx. This removes only `/v2/`; it does not change the Dashboard release or credentials.

<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.15
Purpose: Specify V2 fixture workspace, authenticated same-origin Grace chat, and bounded LAN routes
Authority: Fixture presentation; chat account/session and exact grants remain Dashboard-authorized
Changed: 2026-10-20 UTC | RV-WEB-V2-GRACE-CHAT-002 | Record mounted route, authenticated API integration, and current browser acceptance prerequisite
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell

**Tasks:** `RV-WEB-V2-SHELL-001` (fixture shell), `RV-WEB-V2-LAN-PREVIEW-001` (authenticated LAN access), `RV-WEB-V2-SNAPSHOT-001` (V2 local snapshot), and `RV-WEB-V2-GRACE-CHAT-002` (same-origin authenticated Grace chat) · **Owner:** Windows C1 · **Classification:** isolated frontend enhancement / LAN route integration.

**Component:** `RIVERVIEW-V2-WORKSPACE-SHELL` · **Milestone:** issue #164 parallel V2 shell.

**Execution model:** interactive frontend, request-driven same-origin API calls for Grace account/conversation operations, and static frontend delivery through either the isolated Python preview or the authorized LAN HTTPS `/v2/` mount. V2 owns no database or background worker; Dashboard persists conversations and authorizes every read/send.

## Ready, design, and boundaries

Issue #164 requests a parallel workspace-first interface while V1 remains the default. This task provides the first shell slice: compact navigation; resident directory selection; persistent resident/conversation context; and overview, work, resources, knowledge, ChatGPT, and Comms5 surfaces. A session-scoped in-memory selection survives view changes. All content is visibly identified as fixture or preview data. Grace is represented only by a verified name from the requested shell context; this does not assert a live resident profile or expose Grace data. Other residents and work items are synthetic.

V2 has two intentionally different delivery routes. The optional Python preview is a fixture-only HTTP surface on loopback or the trusted LAN; it retains the existing salted-password, Host/subnet/Origin/one-use-CSRF controls, rejects writes, and V2's chat client refuses to call the Dashboard from that HTTP origin. The integrated route is `https://192.168.1.155/v2/`, served as static files by Nginx inside the already LAN-restricted TLS server. Nginx's inherited Host/Origin/LAN checks remain in force; `deploy/nginx/riverview-v2.location.conf` adds only the `/v2/` path with a strict same-origin CSP and no-store response headers. The existing `/` and `/api/v1/` proxy routing remains unchanged. The static bundle is copied into a versioned, www-data-readable release directory under `/var/www/riverview-v2-preview/releases/`; no new listener, firewall rule, DNS, or public route is created.

The V2 chat UI uses the existing Dashboard account API directly at the same HTTPS origin. It checks the current account session with `GET /api/v1/auth/session`; when absent, the user signs in via `POST /api/v1/auth/session`. Dashboard sets an HttpOnly account cookie and a SameSite CSRF cookie. V2 never reads or stores the account cookie/password/token. It sends the CSRF value in `X-Riverview-CSRF` for state-changing requests and establishes a conversation session using `POST /api/v1/resident/conversation-session`. The existing Dashboard server verifies the Steward account, current binding, and exact `resident.conversation.read` and `.send` grants. V2 then calls the existing list/history, streamed send, and response-status endpoints. Durable append-only Dashboard events are authoritative. Browser localStorage contains only the selected conversation ID; message bodies remain in Dashboard persistence and are rendered with text nodes. Failed or uncertain sends are never automatically repeated. Pending responses are inspected with read-only status requests and resume after reload by examining durable history.

Theme selection (`Light`, `Dark`, `System`) is persisted under `rv.v2.theme`; resident selection and sidebar state remain in memory. Sidebars independently cycle through expanded, icon-only/compact, and hidden states. Controls expose keyboard-visible descriptions and focus outlines. ChatGPT remains a separate external link, while Comms5 remains **UNVERIFIED** because the live contract still has no independently recorded, correlated send/receive event projection. The enabled `Snapshot` button builds a local bounded ZIP from the active V2 view. Its communication metadata reports the observed Grace connection/history state without message content, IDs, identity, credentials, or error payloads; Comms5 counts remain null. The 2 MiB hard limit and SHA-256 manifest remain in force. Snapshot makes no API request of its own and does not claim GitHub archive success.

## V1 parity and integration boundary

The current V1 dashboard remains authoritative for live system status, Grace/CME projections, authenticated account/session behavior, diagnostic snapshot packaging, and private GitHub archival. The V2 preview preserves the workspace navigation and presentation intent but currently has fixture-only residents, work, resource and knowledge cards. It does not consume V1 endpoints or share V1 credentials. The V1 archive worker's draft (PR #168) uses the authenticated V1 API and V1 page diagnostics, so its capture and archive endpoint are not called by V2. V2 independently reuses the ZIP store format, hard-bound discipline, explicit structured-member checksums, and allowlist redaction pattern. GitHub archive upload remains a later integration requiring an approved V2 identity/authorization contract and server endpoint; no credential or V1 data is borrowed.

Chat contract: deployed V1 release `cf4a97e2a712e05e5c5d0a4a82d1016df5ed2ba1` implements `rv.resident.conversation.v1`. The same-origin server API establishes an HttpOnly `rv_account_session` and CSRF cookie, then a conversation cookie scoped to `/api/v1/resident/conversations`. It rechecks the account session/CSRF and exact `resident.conversation.read/send` grants on every applicable request; history/messages are durable append-only events. The V2 `/v2/` route shares the exact HTTPS origin and calls this API directly; there is no V2 server-side credential proxy. The previous cross-origin handoff is retired. The legacy HTTP preview is not an authenticated Dashboard origin and its V2 chat client remains disabled there.

Comms5 boundary: the authenticated Comms5 v5 capability contract on Camrui exposes bounded governed operations and a read-only `transport_probe`; it does not expose V2 a general outbound/inbound message ledger with inspectable payloads and correlated lifecycle stages. V2 reports traffic counts as **UNVERIFIED** and uses `null` for unknown counts; it does not infer zero or claim external ChatGPT escalation. Snapshot metadata records only this integration status and does not capture conversation text, Comms5 payloads, credentials, or correlation IDs.

The LAN login stores no cleartext password. A one-time hidden prompt writes a random-salt PBKDF2-HMAC-SHA256 verifier (600,000 iterations) in an owner-only file with mode 0600. The process creates an eight-hour HMAC-signed, HttpOnly, SameSite=Strict session cookie; its signing key is ephemeral and held only in memory, so restarting the preview invalidates sessions. Five failed password attempts from one client in a 15-minute window trigger a 15-minute in-memory lockout. Requests and form contents are not logged. The direct LAN URL uses HTTP: the password and cookie are not encrypted in transit. Use it only on the trusted Riverview LAN, never on public or untrusted networks.

The existing V1 is a Python standard-library service with static assets, a bearer-protected `rv.dashboard.v1` API, read-only PostgreSQL projections, and narrowly scoped notification-receipt writes. It is deployed separately from this code. This implementation does not reuse or call its API. V1 stays unchanged and is not a dependency.

## Interfaces and operations

Run from a checkout for local development:

```sh
python3 scripts/serve_v2_workspace_preview.py --host 127.0.0.1 --port 8877
```

Open `http://127.0.0.1:8877/` on the checkout host. This default has no password because it accepts loopback connections only.

### Trusted-LAN preview

The current Camrui interface was verified as `192.168.1.155/24`; the Steward's Windows development PC was last recorded as `192.168.1.88`. The operator must confirm both addresses before starting the LAN listener.

On Camrui, the Steward chooses a password locally through the hidden prompt. It is not supplied as a command argument, printed, or sent to GitHub:

```sh
python3 scripts/setup_v2_workspace_preview_auth.py
```

The tool writes only the salted hash to `/home/admin1/.config/riverview/v2-preview-auth.json` with owner-only permissions. Start the preview bound to the Camrui LAN address and its /24, never to `0.0.0.0`:

```sh
python3 scripts/serve_v2_workspace_preview.py --host 192.168.1.155 --port 8877 --trusted-network 192.168.1.0/24 --auth-file /home/admin1/.config/riverview/v2-preview-auth.json
```

The server refuses any non-loopback start without all three settings and a valid owner-only hash file. From Chrome on a trusted Riverview LAN device, open `http://192.168.1.155:8877/` and enter the chosen password once; the cookie lasts eight hours or until preview restart. This is a foreground preview process, not an installed service. No firewall rule, public route, Nginx route, or V1 change is included. Host firewall status showed UFW inactive; lower-level rules were not inspectable without root. Existing Nginx HTTPS currently serves V1 at the site root; reusing it for V2 would require a separate production Nginx change and is not part of this task.

The password setup and LAN command are one-time operator commissioning steps. The ordinary V2 user flow requires only the URL and the Steward-chosen password; it does not require SSH, bearer tokens, CLI access, or a machine-generated user credential. The preview remains limited to synthetic/read-only fixture content.

Future authoritative residents, assignments, work, model/resource controls, and communications need explicit API contracts, governed identity/authorization, privacy review, and component acceptance. Do not substitute fixtures for those contracts or infer permission from a visible action.

## Acceptance criteria and evidence

1. V1 source, runtime, Nginx route, and production data remain unchanged.
2. Default mode serves static files on loopback and refuses unsafe methods/path escapes.
3. LAN mode binds only to the explicit Camrui IPv4 address, checks the configured /24 and Host, and requires password auth before serving any shell asset. Login requires a fresh, client-bound, one-use CSRF token; a present non-null Origin must match the exact HTTP authority, while absent or `null` Origin is accepted only with that token.
4. Password storage contains only algorithm/work factor, random salt, and derived hash in an owner-only file; failures are rate-limited and authenticated responses are non-cacheable.
5. Authentication uses an eight-hour signed HttpOnly/SameSite cookie with in-memory key; no secret appears in source, browser storage, command arguments, or request logs.
6. Navigation and resident selection work in browser memory; view switching retains selected context.
7. Grace API calls are same-origin HTTPS only and use the existing Dashboard session, CSRF protection, resident binding, and exact grants. The HTTP fixture preview makes no API calls. Desktop and phone layouts fit their viewport.
8. Recovery is local: stop and restart only the preview command. No migration or rollback of V1 is involved.

Run the offline and browser checks from the checkout root:

```sh
python3 -m unittest tests.test_v2_workspace_shell -v
python3 scripts/verify_v2_workspace_browser.py --base-url http://127.0.0.1:8877
node scripts/verify_v2_workspace_mobile.cjs --url http://127.0.0.1:8877/
python3 scripts/process_graph.py validate
python3 scripts/process_graph.py check
```

Add LAN-mode acceptance using a disposable in-memory test hash: verify unauthenticated root shows only the login screen, assets return 401, correct password receives a session cookie and serves assets, invalid Host/Origin and non-LAN source are rejected, five failed attempts produce 429 with Retry-After, and restart invalidates the cookie. Final target acceptance also requires Chrome from the actual Windows development PC; local host tests alone do not satisfy this.

Browser navigation timings measure the synchronous in-memory view switch handler; viewport width/overflow checks measure actual rendered layout. They do not claim API load or production readiness.

See [troubleshooting and recovery](RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md) and the generated [shell process flow](RIVERVIEW_V2_WORKSPACE_SHELL_FLOW.md). Structural process-graph consistency is checked by `python3 scripts/process_graph.py check`; automated and browser verification commands are recorded with issue #164.

## Lifecycle applicability matrix

| Lifecycle stage | Applicability and evidence | Status / next action |
| --- | --- | --- |
| Definition of Ready | Issue #164 defines a parallel workspace-first shell and then password-protected trusted-LAN preview, with V1 default and no production changes. LAN address, operator password setup, narrow source subnet, execution model, and acceptance plan are explicit. | PASS for this increment |
| Design | Fixture-only shell; default loopback mode; explicit-IP LAN mode; salted password hash; Origin/Host/subnet checks; bounded sessions, rate-limits and request concurrency; HTTP privacy boundary; local recovery. | PASS |
| Pre-change preservation | Exact prior bytes and SHA-256 are recorded per controlled file in `.riverview-backups/manifest.jsonl`; changed existing files have revision-specific restoration copies. Initial files have no predecessor on the clean base and start at 1.0.0. | PASS; check with `scripts/revision_control.py` |
| Implementation | Shell, loopback/LAN preview, local password setup, authentication and subnet checks, tests, cookbook, graph, and generated views are implemented together. | PASS for isolated preview code |
| Automated checkout | Offline auth/security tests, syntax, browser layout, graph consistency, revision/backup audit, and V1 isolation smoke are recorded per source commit. | PASS for this local checkout; headless Chrome on Camrui authenticated to LAN V2 and verified the handoff/telemetry UI and ZIP. Windows Chrome verification of this delta remains pending. |
| Code review | Author self-review covers browser authority, network, method, path, and production isolation boundaries. | PARTIAL; independent review requested through the draft PR if an authorized reviewer is available |
| Deployment / acceptance | Steward authorized this isolated LAN preview. No V1, Nginx, firewall, systemd, traffic, production API, or live data change is included. Actual Windows browser acceptance requires local password setup and a user-side test. | PARTIAL pending the Windows test |
| Operations / maintenance | The foreground preview can be stopped/restarted locally; sessions and lockouts reset on restart. No durable queue or autonomous work exists. | N/A for the static preview; document explicit resume/rollback in the cookbook |

The Rev 1.6 eight-deliverable table below is the component applicability matrix. Deliverables 6 and 7 are N/A only for this isolated presentation shell because it owns neither authoritative operational state nor recurring institutional work; those gates must be reassessed for a live integrated V2 component. The canonical process-graph standard is applicable and met: the shell has a registered JSON workflow and generated Mermaid views. A diagram alone is not runtime evidence; the browser and server checkout supplies the behavior evidence.

## Eight-deliverable component DoD assessment

| Deliverable | State | Evidence / remaining work |
| --- | --- | --- |
| 1. Code and contracts | PARTIAL | Password verifier, owner-only configuration, LAN bind/subnet/Host/Origin/CSRF rules, session, lockout and read-only static interface are versioned. Independent reviewer evidence remains pending. |
| 2. Functionality demonstrated | PARTIAL | Offline auth/security tests plus authenticated Chrome on Camrui verify the current handoff and ZIP. The Steward previously accepted Windows Chrome login/navigation on `d1cd6f3`; Windows Chrome verification of this handoff/telemetry delta remains pending. No V2 chat turn was sent. |
| 3. Complete versioned documentation | PASS for this slice | This specification records execution, interface, authority, dependencies, limitations, preview operation and rollback. |
| 4. Troubleshooting and recovery cookbook | PASS for code checkout | Cookbook records password setup, read-only diagnostics, expected results, failure cases, session/lockout behavior, rollback and resume procedure. |
| 5. Versioned visualization flowcharts | PASS for code paths | Generated focused Mermaid view includes local setup, network admission, authentication, rate-limit, reject, and recovery paths. |
| 6. Steward-level live operational visualization | N/A for this isolated presentation shell | V1 remains the live operational dashboard; this slice has no authoritative operational state, and fixture data cannot satisfy live-view acceptance. Reassess when V2 is integrated with a governed read-only source. |
| 7. Operational autonomy and blocker clearance | N/A for an interactive static preview | It performs no recurring institutional work and owns no durable queue, worker, heartbeat, or escalation. Manual local startup is only for the preview. Integration/acceptance blockers are recorded in issue #164. |
| 8. Registered canonical process graph | PASS | `process_graphs/riverview-v2/workspace-shell.json` validates with globally unique IDs and typed runtime/diagnostic/recovery edges; generated views pass `process_graph.py check`. |

The prior Snapshot increment adds the V2-only local ZIP flow. This communication increment adds a direct Dashboard handoff and truthful V2 integration metadata in the ZIP. It does not connect V2 to the Dashboard API or Comms5. Real Grace messages/history remain available in V1; direct V2 chat and Comms5 counters/payload inspection remain blocked at the authentication and telemetry boundaries above.

**Overall:** the preview remains **PARTIAL / not a production release**. LAN login and basic navigation were previously accepted by the Steward on `d1cd6f3`; Snapshot ZIP acceptance is complete; this increment's handoff and truthful Comms5 state pass authenticated Chrome on Camrui. Windows Chrome confirmation of this new handoff/telemetry UI and independent code review remain pending. No V2 Grace message was sent.

### Cross-cutting gates

- **Execution model:** interactive browser shell plus request-driven foreground static preview. Session and failed-login state are in memory and reset on restart; the password hash remains in the owner-only local config file. No recurring work source or autonomous task is represented.
- **External observability:** N/A for an independently operated service because there is no service lifecycle or authoritative V2 status. The local startup URL and HTTP status are diagnostic only and are not health/heartbeat claims. V1 retains its own observability contract.
- **Blockers:** Windows Chrome confirmation of this new handoff/telemetry UI; independent code review; V2 principal-bound chat session; authorized Comms5 event projection; future V2 resident/resource data contract and GitHub archive authorization. The preview password was already commissioned; no production action is pending or performed here.

## V2 preview usability increment and feature-parity register

| V1 capability | V2 preview status | Truthful state / next dependency |
| --- | --- | --- |
| Live Dashboard / Grace / CME status and freshness | Not integrated | V1 remains authoritative; V2 fixtures are not live status. Needs an approved read-only projection, identity and authorization contract. |
| Account login and Steward authorization | Preview-only LAN password | Separate local preview auth; no V1 session reuse or production identity integration. |
| Diagnostic Snapshot | Enabled `Snapshot` control creates a local ZIP | Bounded V2 fixture/browser state and manifest are included; no upload or live data. GitHub archive needs a separately reviewed V2 auth/API contract. |
| Resident conversation / Grace chat | Integrated same-origin Dashboard API | The deployed V1 API supports durable authenticated Grace history and message exchange. V2 uses that HTTPS API directly; the HTTP fixture preview remains disconnected. Real Chrome send/receive/reload acceptance is pending a trusted Chrome profile and authorized Dashboard session. |
| ChatGPT external client | External link only | Opens chatgpt.com; no Riverview context transfer or Grace connection. |
| Comms5 communication channel | **UNVERIFIED** in V2 | The Comms5 contract is available on Camrui, but V2 has no authorized general message-event feed for independent send/receive counters, payload inspection, and correlation stages. Unknown counts remain null. |
| Fixture navigation/resources/knowledge | Implemented locally | Synthetic/read-only fixture content only; selection stays in memory. |
| Theme and sidebars | Implemented in V2 preview | Light/Dark/System; left and right independently cycle expanded/compact/hidden; theme choice alone persists locally. |

The local Snapshot feature is implemented and tested. It now includes truthful V2 chat/Comms5 connection diagnostics but no message contents or fabricated counters. Archive-to-GitHub, live server diagnostics, pixel screenshot capture, direct V2 resident conversations, V1 API use, dashboard projection, and V2 account identity remain unconnected. The Dashboard and Comms5 services were inspected read-only; no V1 endpoint, credential, or production configuration was changed.

This is not a claim that issue #164 or a deployed V2 component is fully accepted.

### RV-WEB-V2-GRACE-CHAT-001 lifecycle and acceptance

**Owner:** Windows C1 · **Component:** `RIVERVIEW-V2-WORKSPACE-SHELL` · **Classification:** enhancement with an integration blocker · **Execution:** interactive browser shell; request-driven preview server. **Scope:** inspect existing interfaces; add a secure link to the deployed authenticated Grace chat; expose truthful Comms5 status in V2 and its local Snapshot; update tests, recovery guidance, graph, and evidence. V1 and production services/configuration remain read-only. **Dependencies:** deployed Dashboard release `cf4a97e2`; V2 LAN password session; Comms5 v5 capabilities. **Acceptance:** no browser API or credential transfer; handoff opens the actual Dashboard Grace view; unknown Comms5 counts remain explicitly unverified; Snapshot contains redacted integration status; current browser preview and offline/security checks pass. The requested in-V2 send/receive round trip is blocked until a separately authorized same-origin identity/session path exists.

| DoD 1.6 deliverable | Status for this increment | Evidence / limitation |
| --- | --- | --- |
| 1. Code and contracts | PARTIAL | V2 handoff and unverified diagnostic contract added; no V2 authenticated conversation adapter exists. |
| 2. Functionality demonstrated | PARTIAL | Browser verifies link, unavailable state, redaction, and snapshot. No Grace message was sent from V2, and no V2 durable history is claimed. |
| 3. Versioned documentation | PASS for implemented scope | Live V1 contract/version and V2 origin/auth boundary recorded above. |
| 4. Troubleshooting/recovery | PASS for implemented scope | Cookbook identifies handoff, expected state, and resume/rollback. |
| 5. Versioned visualization | PASS for implemented scope | Canonical graph includes handoff, unverified Comms5 state, snapshot diagnostics, and recovery. |
| 6. Steward live view | N/A for static preview | V1 remains the authoritative live view. |
| 7. Operational autonomy | N/A for interactive preview | V2 has no recurring work or worker. The authentication decision is recorded as an external blocker. |
| 8. Registered canonical graph | PASS after validation | `workspace-shell.json` and generated flow are synchronized. |

**Blocker register:** `RV-V2-AUTH-ORIGIN-001` (authorization/security dependency). Detection: V2 runs on HTTP `192.168.1.155:8877`; V1 chat is HTTPS same-origin, no-CORS, bearer/account authenticated, exact-grant gated, and cookie protected. Owner/decision: Steward plus Dashboard owner. Required authority: separately approve a reviewed same-origin identity/session integration or V2 deployment/auth design that preserves exact grants and V1. Timeout/durable state: pending, recorded in issue #164; no automatic retry or bypass. Resume: implement only after a reviewed contract grants V2 a principal-bound session. `RV-V2-COMMS5-TELEMETRY-001` (capability dependency): no general message event feed/counter operation exists in Comms5 v5 capabilities; owner: Comms5 contract owner; resume after an independently auditable transport projection is authorized and available. No number, payload, or external escalation is inferred.

### RV-WEB-V2-GRACE-CHAT-002 current integration and acceptance

This later task supersedes the preceding handoff-only status. It adds the LAN-only Nginx static mount at `https://192.168.1.155/v2/`; the pre-existing LAN `/24` allow rule, Host/Origin checks, TLS certificate, `/` route and `/api/v1/` proxy remain unchanged. V2 then calls the same-origin Dashboard account/session, conversation-session, history, streamed send and response-status endpoints. HttpOnly/Secure cookies, CSRF, Steward identity, resident binding and exact `resident.conversation.read/send` grants remain Dashboard-authorized on every applicable request. Durable Dashboard events are rendered as text nodes; only the selected conversation ID is stored locally. Comms5 send/receive counters and inspectable messages remain **UNVERIFIED** with unknown counts `null`.

Checkout evidence: 20/20 focused tests pass; JavaScript/Python syntax, `git diff --check`, the 14 registered process graphs (296 nodes), and revision/predecessor audit pass. After the authorized Nginx route reload, `/` and `/v2/` return 200, unauthenticated conversation API returns 401, invalid Host is rejected, and the Dashboard service remains active at the same PID with zero restarts. No database, Dashboard service or Grace worker was changed.

The real Chrome send/receive/reload step is **pending**. Chrome on Camrui rejects the LAN certificate until its profile trusts the verified Riverview LAN Root CA (`ERR_CERT_AUTHORITY_INVALID`). The isolated temporary Chrome profile trusted the public CA but had no authorized Dashboard session. No message was sent. The remaining operator prerequisite is a Chrome profile that both trusts this CA and has an authorized Dashboard Steward session (or the Steward must enter credentials through the hidden local prompt). Run `python3 scripts/verify_v2_grace_chat_chrome.py --evidence-dir <protected-evidence-dir>` once after that prerequisite; it sends one harmless unique prompt, checks durable user/Grace events and timestamps/sequences after reload, and stores no transcript or credentials. It never automatically retries an uncertain send.

The exact Nginx predecessor is protected at `/var/lib/riverview/engineering-backups/RV-WEB-V2-GRACE-CHAT-002/riverview-lan.predecessor` with SHA-256 `0878b2eb61d19f73a36e642acaf0ef3c6b2301188ac1f6eb0c10baf1d82b6c14`. Follow the protected `RESTORE.txt`: restore the predecessor, verify its checksum, run `sudo nginx -t`, and gracefully reload Nginx to remove only `/v2/`; do not restart Dashboard.

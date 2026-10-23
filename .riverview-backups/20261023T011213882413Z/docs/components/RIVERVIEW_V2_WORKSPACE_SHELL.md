<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.32
Purpose: Specify V2 workspace, center-mounted authenticated Grace chat, and bounded LAN routes
Authority: Fixture presentation; chat account/session and exact grants remain Dashboard-authorized
Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Connect authenticated Hardware view to host telemetry.
Changed: 2026-10-21 UTC | RV-V2-WORK-INTEGRATION-DEPLOY | Integrate Work over the deployed Hardware and Snapshot composite
Changed: 2026-10-21 UTC | RV-V2-OCTO1-DIGITAL-TWIN | Add interactive OCTO1 topology and a source-bounded live activity view
Changed: 2026-10-21 UTC | RV-V2-OCTO1-GRACE-TRACE-001 | Read a content-free trace from the authorized durable Grace conversation API
Changed: 2026-10-21 UTC | RV-V2-OCTO1-PHYSICAL-TWIN-001 | Render supplied X12 Ultra manufacturer references with interactive, source-bounded selections
Changed: 2026-10-22 UTC | RV-V2-GRACE-MESSAGE-ACTIONS-001 | Document stable keyed history reconciliation, transcript copy, and authorized conversation objective intake.
Changed: 2026-10-22 UTC | RV-V2-MOUNTED-STORAGE-001 | Document unique measured storage aggregation and explicit unconfigured host capacity.
Changed: 2026-10-22 UTC | RV-V2-WEBSITE-INTEGRATION-20261022 | Record read-only 12-sample model slot observation and request-attribution limit.
Changed: 2026-10-22 UTC | RV-V2-GPU-REFRESH-STABILITY | Keep measured GPU cards mounted during five-second refresh; mark retained samples stale on source failure
Changed: 2026-10-22 UTC | RV-V2-HW-AI-ENHANCEMENTS-207 | Document VRAM bars, measured router response-rate traces, slot context, and bounded activity paging
Changed: 2026-10-22 UTC | RV-HW-LIVE-STREAM-ACTIVITY-001 | Document content-free live streamed-character cadence and native token-counter limitation.
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell

**Tasks:** `RV-WEB-V2-SHELL-001` (fixture shell), `RV-WEB-V2-LAN-PREVIEW-001` (authenticated LAN access), `RV-WEB-V2-SNAPSHOT-001` (V2 local snapshot), and `RV-WEB-V2-GRACE-CHAT-002` (same-origin authenticated Grace chat), and `RV-WEB-V2-GRACE-WORKSPACE-003` (center workspace layout) · **Owner:** Windows C1 · **Classification:** isolated frontend enhancement / LAN route integration.

**Component:** `RIVERVIEW-V2-WORKSPACE-SHELL` · **Milestone:** issue #164 parallel V2 shell.

**Execution model:** interactive frontend, request-driven same-origin API calls for Grace account/conversation operations, and static frontend delivery through either the isolated Python preview or the authorized LAN HTTPS `/v2/` mount. V2 owns no database or background worker; Dashboard persists conversations and authorizes every read/send.

## Ready, design, and boundaries

Issue #164 requests a parallel workspace-first interface while V1 remains the default. This task provides the first shell slice: compact navigation; resident directory selection; persistent resident/conversation context; and overview, work, resources, knowledge, ChatGPT, and Comms5 surfaces. A session-scoped in-memory selection survives view changes. All content is visibly identified as fixture or preview data. Grace is represented only by a verified name from the requested shell context; this does not assert a live resident profile or expose Grace data. Other residents and work items are synthetic.

V2 has two intentionally different delivery routes. The optional Python preview is a fixture-only HTTP surface on loopback or the trusted LAN; it retains the existing salted-password, Host/subnet/Origin/one-use-CSRF controls, rejects writes, and V2's chat client refuses to call the Dashboard from that HTTP origin. The integrated route is `https://192.168.1.155/v2/`, served as static files by Nginx inside the already LAN-restricted TLS server. Nginx's inherited Host/Origin/LAN checks remain in force; `deploy/nginx/riverview-v2.location.conf` adds only the `/v2/` path with a strict same-origin CSP and no-store response headers. The existing `/` and `/api/v1/` proxy routing remains unchanged. The Communications Activity preview release uses `/var/www/riverview-v2-preview/releases/RV-WEB-V2-COMMS-ACTIVITY-001/`, selected only by the V2 location alias. Its deployment preserves the previous include, validates with `nginx -t`, and reloads Nginx gracefully; no new listener, firewall rule, DNS, or public route is created.

The V2 chat UI uses the existing Dashboard account API directly at the same HTTPS origin. It checks the current account session with `GET /api/v1/auth/session`; when absent, the user signs in via `POST /api/v1/auth/session`. Dashboard sets an HttpOnly account cookie and a SameSite CSRF cookie. V2 never reads or stores the account cookie/password/token. It sends the CSRF value in `X-Riverview-CSRF` for state-changing requests and establishes a conversation session using `POST /api/v1/resident/conversation-session`. The existing Dashboard server verifies the Steward account, current binding, and exact `resident.conversation.read` and `.send` grants. V2 then calls the existing list/history, streamed send, and response-status endpoints. Durable append-only Dashboard events are authoritative. Browser localStorage contains only the selected conversation ID; message bodies remain in Dashboard persistence and are rendered with text nodes. Failed or uncertain sends are never automatically repeated. Pending responses are inspected with read-only status requests and resume after reload by examining durable history.

Theme selection (`Light`, `Dark`, `System`) is persisted under `rv.v2.theme`; resident selection and sidebar state remain in memory. Sidebars independently cycle through expanded, icon-only/compact, and hidden states. Controls expose keyboard-visible descriptions and focus outlines. ChatGPT remains a separate external link, while Comms5 remains **UNVERIFIED** because the live contract still has no independently recorded, correlated send/receive event projection. The enabled `Snapshot` button builds a local bounded ZIP from the active V2 view. Its communication metadata reports the observed Grace connection/history state without message content, IDs, identity, credentials, or error payloads; Comms5 counts remain null. The 2 MiB hard limit and SHA-256 manifest remain in force. Snapshot makes no API request of its own and does not claim GitHub archive success.

## Hardware & AI telemetry enhancements (Issue #207)

Each retained GPU card displays a visual VRAM bar only when both measured used and total bytes are valid. The adjacent summary shows used/total, percentage, and remaining capacity; missing, inconsistent, stale, or failed telemetry is never converted to zero. The five-second refresh updates keyed nodes in place and keeps the existing single-flight request guard.

The model response-throughput charts use only successful durable Grace provider attempts that include output-token count, elapsed provider-call milliseconds, and an end timestamp. A point is output tokens divided by the router-recorded provider-call interval, so it includes endpoint and transport overhead; it is not server-only GPU throughput. The rolling window is five minutes, updated with the authenticated trace poll. Prompt-processing/generation split times are unavailable because the current llama.cpp servers return HTTP 501 for `/metrics` and `/slots` does not contain those timings. Missing 80B/30B samples remain explicitly unavailable.

Selected 80B/30B details use only the Dashboard's authenticated, bounded numeric `slot_context` projection from fixed llama.cpp `/slots` endpoints. Configured context is reported per slot; the server-wide capacity is the sum of those per-slot limits and is labeled as such. Prompt counts and processed/cached counts appear only when numeric counters are present. KV-cache allocation bytes and queue depth are unavailable from these model-server builds. Raw task identifiers, prompts, and token data are not returned by the Dashboard projection.

Live model activity is separate from completed token-throughput points. Dashboard adds an owner/conversation-authorized `/api/v1/resident/conversations/{id}/stream-activity?limit=12` projection of the same durable stream rows; it exposes request IDs, stage/provider/model, status, generation, event sequence, timestamps, and bounded character counts, never delta text. V2 computes received text characters per second only from adjacent positive timestamp intervals and labels it `characters/s`; it is application-side delivery cadence, not token throughput or GPU compute. One delta shows generation active while awaiting another sample. Stale/unavailable stream reads retain prior points with a stale label. llama.cpp `/metrics` remains HTTP 501 and `/slots` has no live output-token counters, so native token-generation speed remains unavailable.

Recent Hardware Activity retains at most 60 browser-side samples and shows four per page. Previous/Next changes the visible page without resetting on telemetry refresh. The selected page and activity scroll offset are retained while visible items update; only the current page's four keyed records are mounted. Server-side diagnostic retention is unchanged.

## Grace center workspace (RV-WEB-V2-GRACE-WORKSPACE-003)

The overview remains an overview when its navigation item is selected. From **Residents**, selecting the real Grace entry opens a dedicated center-column conversation workspace; the authenticated chat section is mounted under `#workspace-main`, never inside `#right-sidebar`. The persistent right sidebar retains selected-resident and ChatGPT/Comms5 support context. Selecting either synthetic resident keeps the fixture directory active and never opens or implies a live conversation. The Residents navigation item remains selected while the Grace conversation is displayed, and selecting Overview returns to the overview.

The existing `grace-chat.js` client and Dashboard contracts are unchanged: cookie/CSRF authentication, Steward identity, exact read/send grants, durable event history, send receipt, read-only response status, and reload recovery still belong to the same-origin Dashboard API. The larger center layout gives history the available vertical space and keeps the composer at the bottom of its chat card. Mobile Chrome uses the same single-column chat with a viewport-contained history and composer. The V2 Snapshot records `grace-conversation` versus the chosen fixture view and the observed chat connection status; it excludes transcript text, IDs, account identity, and credentials.

## V1 parity and integration boundary

The current V1 dashboard remains authoritative for live system status, Grace/CME projections, authenticated account/session behavior, diagnostic snapshot packaging, and private GitHub archival. V2 workspace views still use fixture-only residents, work, resource and knowledge cards; its Grace chat alone consumes the existing V1 conversation API through same-origin HTTPS and Dashboard-owned authorization. V2 does not borrow a bearer credential or proxy server-side identity. The V1 archive worker's draft (PR #168) uses the authenticated V1 API and V1 page diagnostics, so its capture and archive endpoint are not called by V2. V2 independently reuses the ZIP store format, hard-bound discipline, explicit structured-member checksums, and allowlist redaction pattern. GitHub archive upload remains a later integration requiring an approved V2 identity/authorization contract and server endpoint; no credential or V1 data is borrowed.

Chat contract: deployed V1 release `cf4a97e2a712e05e5c5d0a4a82d1016df5ed2ba1` implements `rv.resident.conversation.v1`. The same-origin server API establishes an HttpOnly `rv_account_session` and CSRF cookie, then a conversation cookie scoped to `/api/v1/resident/conversations`. It rechecks the account session/CSRF and exact `resident.conversation.read/send` grants on every applicable request; history/messages are durable append-only events. The V2 `/v2/` route shares the exact HTTPS origin and calls this API directly; there is no V2 server-side credential proxy. The previous cross-origin handoff is retired. The legacy HTTP preview is not an authenticated Dashboard origin and its V2 chat client remains disabled there.

Comms5 boundary: the authenticated Comms5 v5 capability contract on Camrui exposes bounded governed operations and a read-only `transport_probe`; it does not expose V2 a general outbound/inbound message ledger with inspectable payloads and correlated lifecycle stages. V2 reports traffic counts as **UNVERIFIED** and uses `null` for unknown counts; it does not infer zero or claim external ChatGPT escalation. Snapshot metadata records only this integration status and does not capture conversation text, Comms5 payloads, credentials, or correlation IDs.

### Communications Activity monitor (RV-WEB-V2-COMMS-ACTIVITY-001)

The left navigation opens a dedicated Communications Activity workspace. It presents time-window, status, direction, and text-search controls; a timestamped event table; selected-event detail area; summary counters; source state; and a refresh/check control. This is a presentation surface, not a new communications backend. At this revision there is no authorized V2-readable Comms5 activity API. The workspace therefore starts as **UNVERIFIED**, displays each unknown counter as `Unavailable`, renders no event rows, and states that an empty view is not evidence of zero traffic. Search and filters operate on the returned event set when a source is supplied; they do not create or infer records.

`Check source` currently performs only a local configuration check. It sends no network request because no authorized source is configured. The UI records the local check time and keeps the source UNVERIFIED. It does not call the privileged dashboard event API, Comms5 write operations, external-reasoning request/claim/submit operations, or the generic transport probe. No bearer token, message body, authorization code, cookie, or private exchange payload is used in the browser. The right-sidebar Comms5 diagnostic and Snapshot continue to report unknown counters as null; the V2 Snapshot includes safe state and local check time only.

#### Required read-only feed contract before connecting data

A future backend integration must provide a versioned same-origin, read-only API authorized by the existing Dashboard session and a narrowly scoped server-side identity. The browser must never receive a Comms5/provider bearer. The projection should include `schema`, `source_id`, `status`, `observed_at`, `stale_after`, selected-window semantics, nullable directional/status counts, and a bounded event array. Each event may expose only `event_id`, `occurred_at`, `direction`, `destination_label`, `status`, `correlation_id`, and allowlisted redacted diagnostic metadata. It must exclude body/content, credentials, tokens, unrestricted event payloads, and unrelated institutional events. Delivery/receipt/completion labels require corresponding authoritative events; a request accepted by a transport is not proof of delivery. The server must apply the current authenticated Steward identity, exact read grant, row/scope limits, redaction, and retention rules before returning data. Until this contract exists and is independently verified, the monitor stays UNVERIFIED and does not issue an API call.

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

### Work status integration (RV-V2-CAPABILITY-INTEGRATION-P1)

The integrated V2 release includes a request-driven, read-only Work panel backed by Dashboard projections. In the target authenticated LAN HTTPS release, it checks the existing account session before requesting `/api/v1/objectives?limit=25` and `/api/v1/assignments?limit=25`. It shows persisted lifecycle and progress summaries; it omits private human request text, acceptance criteria, artifact paths/digests, and event payloads. No polling, write endpoint, model host, new grant, or new backend component was added. Clearly labeled fixture work cards remain below the summaries and are not represented as production records. The Work panel is deployed in immutable release `RV-WEB-V2-WORK-INTEGRATION-20261021-01`. The deployment retained the deployed Snapshot script and server-injected `authenticated-dashboard` marker, existing Hardware/Communications files, V1 routes, and Nginx authentication controls. Its fallback path is the preserved `RV-WEB-V2-C2-ARCHIVE-6733F29D` release.

The capability-by-capability mapping among V2, historical Estate Office sources, and the current Riverview backend is in [RIVERVIEW_V2_CAPABILITY_MATRIX.md](RIVERVIEW_V2_CAPABILITY_MATRIX.md). That matrix distinguishes current connected contracts from historical-only file views and available-but-not-yet-exposed Dashboard projections. Hardware per-GPU values and Comms5 activity remain unavailable/unverified.

The deployment was built from the current C2 composite release, not from the stale full-tree snapshot in PR #166. Snapshot behavior is served from the verified deployed script, and the Nginx marker injection remains unchanged. Anonymous access continues to stop at the existing Dashboard authentication boundary.

Focused tests use a browser VM with mocked Dashboard responses and assert auth gating, exact same-origin GET calls, redacted output, and non-mutating behavior. These are source-level integration checks; they do not claim live authenticated production data or Windows Chrome acceptance. See the Phase 1 record in the cookbook.

1. V1 source, runtime, Nginx route, and production data remain unchanged.
2. Default mode serves static files on loopback and refuses unsafe methods/path escapes.
3. LAN mode binds only to the explicit Camrui IPv4 address, checks the configured /24 and Host, and requires password auth before serving any shell asset. Login requires a fresh, client-bound, one-use CSRF token; a present non-null Origin must match the exact HTTP authority, while absent or `null` Origin is accepted only with that token.
4. Password storage contains only algorithm/work factor, random salt, and derived hash in an owner-only file; failures are rate-limited and authenticated responses are non-cacheable.
5. Authentication uses an eight-hour signed HttpOnly/SameSite cookie with in-memory key; no secret appears in source, browser storage, command arguments, or request logs.
6. Navigation and resident selection work in browser memory; view switching retains selected context. Selecting Grace from Residents opens the full-size center conversation while Overview and synthetic residents stay in their own views.
7. Grace API calls are same-origin HTTPS only and use the existing Dashboard session, CSRF protection, resident binding, and exact grants. The HTTP fixture preview makes no API calls. Desktop and phone layouts place the chat in the center workspace without horizontal overflow.
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
| Automated checkout | Offline auth/security tests, syntax, browser layout, graph consistency, revision/backup audit, and V1 isolation checks are recorded per source commit. | See the RV-WEB-V2-GRACE-WORKSPACE-003 acceptance record below; real authenticated live chat is not retested from the isolated HTTP runner. |
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

The prior Snapshot increment adds the V2-only local ZIP flow. The authenticated chat increment adds a direct Dashboard connection; this layout increment moves its unchanged client into the center workspace and records the actual selected view in Snapshot metadata. The Dashboard API connection is implemented through the existing authenticated same-origin contract described above. Comms5 counters/payload inspection remain unavailable and are still reported as UNVERIFIED.

**Overall:** the preview remains **PARTIAL / not a production release**. LAN login and basic navigation were previously accepted by the Steward on `d1cd6f3`; Snapshot ZIP acceptance is complete; this increment verifies the center layout and selected-view ZIP in desktop/mobile Chrome. The source-session attempt is blocked by a LAN CA trust error in the existing Camrui Chrome profile; the read-only local runner intentionally uses HTTP and cannot test authenticated sending. The Steward already verified a real durable user/Grace exchange (events 6 and 7) in Windows Chrome before this layout change. No additional live message was sent.

### RV-WEB-V2-GRACE-WORKSPACE-003 acceptance record

**Owner:** Windows C1 · **Classification:** focused frontend enhancement · **Execution:** interactive, browser-owned layout and request-driven existing Dashboard chat API · **Scope:** move the existing Grace client from the supporting right sidebar to the main workspace, correct the obsolete navigation event binding, keep fixture views separate, and report the selected view in the existing redacted Snapshot. No API/backend, database, Nginx, V1, public route, or production service change.

The eight Rev 1.6 deliverables for this assignment are recorded individually:

| Deliverable | Status | Evidence |
| --- | --- | --- |
| 1. Code and contracts | PASS for this UI change | Existing `grace-chat.js`, account cookies, CSRF, server grant checks, durable event order/history, and read-only response polling are unchanged; moved DOM remains under the same V2 center workspace. The stale binding to the removed `conversation-toggle` was deleted. Independent code review remains open at PR #166. |
| 2. Functionality demonstrated | PARTIAL | Chrome 155 on loopback preview exercised Overview → Residents → Grace, main-vs-context placement, fixture separation, Overview return, no console errors, desktop 1440×1000 and emulated mobile 390×844 with no horizontal overflow. Snapshot ZIP verified the selected Grace view and no transcript. This HTTP preview deliberately refuses Dashboard API access; no live send/reply/reload was performed in this run. Steward Windows Chrome already verified durable message events 6/7 on the preceding same-origin implementation. |
| 3. Complete versioned documentation | PASS for this scope | This specification and the recovery cookbook document selection, origin/security boundary, responsive behavior, Snapshot privacy and limitations. |
| 4. Troubleshooting and recovery cookbook | PASS for this scope | Cookbook includes view/asset and mobile-overflow symptoms, diagnostics, expected center placement, and safe local resume. |
| 5. Versioned visualization flowcharts | PASS | Canonical graph now records resident routing, Grace center rendering, fixture continuation, Dashboard session check, and Snapshot metadata behavior. |
| 6. Steward-level live operational visualization | N/A | A frontend layout owns no authoritative operational state; it continues to expose the existing real Grace state through the account UI and safe Snapshot diagnostics, not a new dashboard. |
| 7. Operational autonomy and blocker clearance | N/A | The UI has no recurring work, worker, queue, heartbeat, or autonomous recovery responsibilities. Durable chat and pending-response recovery remain Dashboard-owned and unchanged. |
| 8. Registered canonical process graph | PASS | `process_graph.py validate` and `process_graph.py check` both pass with 14 graphs and 298 nodes. |

Predecessor copies and SHA-256 values are registered in `.riverview-backups/manifest.jsonl`; each modified text file has a revision increase and the graph JSON has an updated sidecar entry. `revision_control.py check --baseline /tmp/rv-v2-workspace-003-baseline.json` passes. Browser test reports and ZIP are retained in the checkout evidence package linked from issue #164 and PR #166. V2 preview deployment was not updated during this assignment. The existing Camrui Chrome page at `/v2/` shows a certificate privacy error, so this run did not claim a live authenticated exchange on the corrected layout.

### Cross-cutting gates

- **Execution model:** interactive browser shell plus request-driven foreground static preview. Session and failed-login state are in memory and reset on restart; the password hash remains in the owner-only local config file. No recurring work source or autonomous task is represented.
- **External observability:** N/A for an independently operated service because there is no service lifecycle or authoritative V2 status. The local startup URL and HTTP status are diagnostic only and are not health/heartbeat claims. V1 retains its own observability contract.
- **Blockers:** Windows Chrome confirmation of this new handoff/telemetry UI; independent code review; V2 principal-bound chat session; authorized Comms5 event projection; future V2 resident/resource data contract and GitHub archive authorization. The preview password was already commissioned; no production action is pending or performed here.

## V2 preview usability increment and feature-parity register

| V1 capability | V2 preview status | Truthful state / next dependency |
| --- | --- | --- |
| Live Dashboard / Grace / CME status and freshness | Not integrated | V1 remains authoritative; V2 fixtures are not live status. Needs an approved read-only projection, identity and authorization contract. |
| Account login and Steward authorization | Dashboard account login on HTTPS `/v2/`; separate preview password on HTTP port 8877 | The integrated route reuses Dashboard-owned secure cookies, CSRF, resident binding and per-operation grants. The isolated HTTP fixture preview retains its separate password and cannot call the API. |
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

### RV-WEB-V2-HW-AI-RESOURCE-001 — Hardware & AI Resource Monitor

The Resources view now reads live measurements through the same-origin authenticated Dashboard. On the LAN HTTPS `/v2/` page, opening Resources checks `GET /api/v1/auth/session`, then requests `GET /api/v1/status` and `GET /api/v1/resources/telemetry` with the existing account session, `credentials: same-origin`, and `cache: no-store`. While Resources remains selected and the browser tab is visible, it requests a new observation every five seconds; leaving the view or hiding the tab stops the timer. An in-flight bounded read may finish, but no overlapping poll is started. It never contacts GPU or inference hosts from the browser. The fixture preview still performs no network requests.

The Dashboard projection is `rv.dashboard.resource-telemetry.v1`. It gathers GPU inventory/metrics from OCTOMINER1 through a dedicated strict-host-key SSH credential whose remote key is forced to the read-only collector. The collector returns device name/index, utilization, VRAM, temperature, power, GPU fan percentage when supported, and allowlisted service labels; host UUIDs and PIDs are discarded. The OCTO1 console joins these current `active_services` labels to the model service projections and displays the resulting GPU group. The join is based on the live host process-to-GPU mapping; it does not infer a physical PCIe slot position. Fixed model API endpoints provide health, loaded model identity, and active slot counts. A loaded model and service readiness are shown separately from slot occupancy. A positive `/slots` processing count is shown as processing, zero as ready/idle, and unavailable fields remain unavailable. This telemetry projection itself does not expose a request ID, server-side prompt/generation phase, or queue depth. Camrui GPU inventory is unavailable; its 0.6B endpoint and model identity can be reported. OctoMiner2 is shown as documented but identity-unverified/unavailable; it is intentionally offline and is not treated as a failure of OCTO1.

The browser renders only response text using DOM text nodes. Source timestamps accompany readings. GPU telemetry cards use stable host/device identities and update metric text in place. A pending refresh keeps the last successful values visible and labels the card refreshing; a failed or expired source labels those retained values stale, never current. The first load shows explicit unavailable text until a reading exists. Polling remains at five seconds while Resources is open and the tab is visible, and overlapping requests are rejected by the existing in-flight guard. Snapshot includes source state and timestamps only; it excludes GPU metric values and loaded model identifiers. The Hardware view does not control, restart, or invoke models. The backend source and secure credential/drop-in contract are documented in the Dashboard component and cookbook.

**Current live source verification (2026-10-21):** Camrui `127.0.0.1:18796` reported `/health` HTTP 200, model `qwen3-0.6b-q8_0-local`, and one idle slot. OCTOMINER1 `192.168.1.160` reported its four P100s serving `Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf`, RTX 4090 serving `Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated.i1-IQ3_XS.gguf`, and RTX 3060 Ti unassigned. `/metrics` returned HTTP 501 on both OCTOMINER1 model servers; queue depth is therefore not available. OCTOMINER2 address `.162` did not respond on the configured inference ports and its SSH identity has not been verified. These are source checks, not a claim of deployed V2 acceptance until the controlled release is activated and checked in the authenticated browser.

#### OCTO1 progressive hardware view (RV-V2-OCTO1-DIGITAL-TWIN)

The Resources page now presents OCTO1 first as an interactive machine console. GPU devices and Grace inference services are selectable; selecting one reveals its current source fields, timestamp, service mapping, readiness, model identity, active slots, and explicit unavailable fields. Device indexes are identifiers only and are never positioned as physical slots. The 80B model currently maps dynamically to the devices whose live host process labels identify `grace-reasoning-80b`; the 30B maps the devices labeled `grace-vision-30b`. A GPU utilization change is not used as a request attribution signal.

The five-second browser timeline is a short in-memory view of timestamped telemetry polls. It shows GPU utilization/temperature/GPU-fan readings and model active-slot state; it never attributes a sample to a request. A separate **Grace request trace** reads the signed-in Steward's current conversation through the existing same-origin, grant-checked history API. It displays only the durable request ID and creation time, router attempt stage/provider, client-side call start/end/outcome, response event time, and returned token counts. Message bodies, raw event metadata, provider model paths, account/session data, and trace IDs in Snapshot diagnostics are excluded. Reads repeat with the authenticated Hardware refresh cadence only while Resources is selected and the browser tab is visible.

The conversation record provides real request creation and correlation inside Riverview, followed by the router's provider-attempt window and a terminal response event after response validation and persistence. `started_at`/`ended_at` are application-side call-boundary timestamps, not model-server receipt or generation timestamps. The current `LocalReasoningProvider.complete_chat()` sends no conversation request ID in its inference HTTP request, and the configured llama.cpp `/slots` response contains occupancy rather than a correlated request ID or prompt/generation phase. `/metrics` returns HTTP 501 and queue depth is unavailable. Therefore server receipt, prompt-processing start, token-generation start/end, and a GPU-to-request mapping remain unverified. Those stages require provider ID propagation plus matching model-server ingress/response instrumentation; this UI does not infer them.

Chassis fan RPM/PWM/control mode/targets, environmental sensors, PSU telemetry, and the watchdog are shown as unavailable because the current OCTO1 Dashboard projection does not expose their controller feed. The historical OctoFan API records describe OCTO2 and are not used as proof of an OCTO1 endpoint or channel mapping. No fan, watchdog, temperature threshold, firmware, or power control exists in this UI.

The four supplied references are now available. The original manufacturer X12 Ultra front/open-chassis artwork is included unchanged at `website/v2/assets/octominer/x12ultra-front-open-chassis-reference.png`; the original watchdog/fan-controller and feature references are included unchanged as `smart-watchdog-fan-controller-reference.png` and `controller-feature-reference.png`. Their recorded SHA-256 values and sizes are in `.riverview-revisions.json`. The earlier Hardware Operations Dashboard concept is used only as visual direction and is not copied into the live asset set or used as physical geometry.

The chassis stage supports front-panel and open-chassis views with selectable five-fan visual positions and front display/control area. Selecting the 80B/30B model or corresponding GPU highlights only the dynamic host process-to-GPU telemetry mapping. No host GPU device is placed on an internal physical bay because no device-to-riser map has been verified. Fan selection labels left-to-right visual position, not controller channel. Controller installation, fan RPM/PWM, sensors, PSU, and watchdog data remain explicitly unavailable; reference illustrations do not establish OCTO1 hardware identity. This is a static read-only V2 visualization. The existing five-second GPU timeline and authorized content-free Grace request trace are preserved as separate evidence channels; server-side request/GPU attribution remains unavailable. Visual browser captures use a clearly marked synthetic fixture and are not live OCTO1 readings or deployment acceptance.

### Stable conversation actions and refresh behavior

Persisted events are reconciled by their durable sequence key. Background history refresh updates role, event time, and body in the existing message nodes instead of replacing the transcript. This preserves open native details menus, scroll offset, conversation identity, and composer value/focus. Menu state is closed only by selection/dismissal or leaving the Grace view. **Copy Conversation Text** copies durable user and Grace messages in chronological order and excludes system status/error events. **Create Work Order** is shown only for a persisted Steward message in a Steward account session and submits `{source_sequence, acceptance_criteria}` to the existing `POST /api/v1/resident/conversations/{conversation_id}/work-orders` path. The server still validates account authority, exact conversation grants, ownership, and idempotency. A returned objective intake receipt is not an execution approval. The menu placement on a conversation message is a temporary UX choice; the follow-up should place the action on an approved proposal revision without changing this existing backend authorization contract.

### Mounted storage capacity

The Resources view displays host-scoped measured mounts from the same authenticated resource telemetry API. It reports mount/device/filesystem identifiers when available, total/used/available bytes, percent used, and last successful observation. The aggregate sums unique `filesystem_id` values only. Host aliases and duplicate filesystem views are not counted twice. The current collector measures Camrui locally and OCTO1 through the restricted existing host command. Windows development and OCTO2 are listed but remain unavailable until their authorized read-only collection path is commissioned; offline or unconfigured storage is never shown as zero. The section performs no disk writes and provides no migration, deletion, or model movement controls.

**Read-only source observation (2026-10-22 19:53:38–19:54:33 UTC):** Twelve five-second reads of the already-configured model health/model/slot APIs observed all three model services ready; the 80B reported one active slot on nine samples and zero on three. The 0.6B and 30B slot counts remained idle. This establishes that the API source provides changing in-progress occupancy; it does not identify a request or establish characters/tokens per second. The live request-cadence graph remains dependent on the authenticated owner-session stream-activity projection and was not observed in an authenticated browser for this task.

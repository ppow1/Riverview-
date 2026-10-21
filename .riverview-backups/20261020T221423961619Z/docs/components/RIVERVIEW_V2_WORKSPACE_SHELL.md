<!--
Changed: 2026-10-20 UTC | RV-WEB-SNAPSHOT-V1-V2-INTEGRATION-001 | Document integrated same-origin snapshot mode while preserving LAN preview isolation.
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.11
Purpose: Specify the isolated V2 browser shell and password-protected LAN preview
Authority: Fixture presentation only; no institutional or production authority
Changed: 2026-10-20 UTC | RV-WEB-V2-SNAPSHOT-001 | Record actual Chrome ZIP acceptance and runtime source identity limits
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell

**Tasks:** `RV-WEB-V2-SHELL-001` (fixture shell) and `RV-WEB-V2-LAN-PREVIEW-001` (authenticated LAN access), and `RV-WEB-V2-SNAPSHOT-001` (V2 local snapshot) · **Owner:** Windows C1 · **Classification:** isolated frontend enhancement / preview operation.

**Component:** `RIVERVIEW-V2-WORKSPACE-SHELL` · **Milestone:** issue #164 parallel V2 shell.

**Execution model:** static browser assets served by an optional foreground Python preview process. The LAN option uses request-driven in-memory session and rate-limit state. No systemd unit, database, production API, or worker.

## Ready, design, and boundaries

Issue #164 requests a parallel workspace-first interface while V1 remains the default. This task provides the first shell slice: compact navigation; resident directory selection; persistent resident/conversation context; and overview, work, resources, knowledge, ChatGPT, and Comms5 surfaces. A session-scoped in-memory selection survives view changes. All content is visibly identified as fixture or preview data. Grace is represented only by a verified name from the requested shell context; this does not assert a live resident profile or expose Grace data. Other residents and work items are synthetic.

The standalone preview has no network-data path. By default its preview server binds only to loopback and serves only `website/v2`. The dashboard-integrated route at `/v2/` is separately served by the existing authenticated dashboard origin and is described below. The optional LAN mode binds to one explicit IPv4 address, requires a narrow client subnet and a local password hash file, and checks the Host header, client address, Origin, and a one-use server-side CSRF token. The login page issues a random, five-minute token bound to the client address; each POST must present a valid unused token. An explicit non-null Origin must match the exact HTTP Host authority. Missing or `null` Origin is accepted only with that token, covering browsers that serialize a form submission with an opaque Origin. Foreign scheme, host, or port is still rejected. Tokens are bounded in memory and discarded on restart. It serves only this static shell and rejects mutating methods other than the password form. The shell retains a `connect-src 'none'` policy. Theme selection (`Light`, `Dark`, `System`) is the only browser preference persisted, under `rv.v2.theme`; resident selection and sidebar state remain in memory. Sidebars independently cycle through expanded, icon-only/compact, and hidden states. Controls expose keyboard-visible descriptions and focus outlines. ChatGPT remains an external client link, Comms5 remains disconnected, and the chat composer is disabled because no authenticated conversation contract exists. The enabled `Snapshot` button remains local-only when served by the standalone preview; it builds a bounded ZIP with V2 view state, member hashes and a local-preview manifest. The 2 MiB hard limit is enforced. This standalone mode excludes cookies, credentials, arbitrary DOM, message contents, live data and server logs, makes no network request, and does not claim GitHub archive success. The standalone preview remains `connect-src 'none'`.

## V1 parity and integration boundary

The current V1 dashboard remains authoritative for live system status, Grace/CME projections, authenticated account/session behavior, the shared snapshot archive endpoint and private GitHub credential. The V2 shell retains fixture-only interface data. Standalone preview does not consume V1 endpoints or share V1 credentials. At `/v2/` on the dashboard origin, V2 uses the existing account session, CSRF and Steward role gate to submit its package through the same archive endpoint; the server credential is not exposed. Its manifest and archive filename identify V2. The integrated mode fetches the common status and operational snapshot projections and adds separate allowlisted V2 interface diagnostics.

Chat gap: V1's status dashboard contract documents resident conversation as not implemented; the V2 shell therefore has no supported resident-chat endpoint to reuse. A real V2 composer needs a separately reviewed authenticated conversation API, resident identity/session binding, authorization, persistence/retention, privacy, failure, and event/observability contracts. The current ChatGPT link only opens chatgpt.com; it does not transfer Riverview resident context or connect Grace. Comms5 remains informational and disconnected.

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
7. No production API reference or browser network connection exists; desktop and phone layouts fit their viewport.
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
| Automated checkout | Offline auth/security tests, syntax, browser layouts, graph consistency, revision/backup audit, and V1 isolation smoke are recorded per source commit. | PASS for local code checkout; actual Windows-client acceptance pending for the Windows-specific UI refinements; V2 Snapshot has local Chrome LAN evidence |
| Code review | Author self-review covers browser authority, network, method, path, and production isolation boundaries. | PARTIAL; independent review requested through the draft PR if an authorized reviewer is available |
| Deployment / acceptance | Steward authorized this isolated LAN preview. No V1, Nginx, firewall, systemd, traffic, production API, or live data change is included. Actual Windows browser acceptance requires local password setup and a user-side test. | PARTIAL pending the Windows test |
| Operations / maintenance | The foreground preview can be stopped/restarted locally; sessions and lockouts reset on restart. No durable queue or autonomous work exists. | N/A for the static preview; document explicit resume/rollback in the cookbook |

The Rev 1.6 eight-deliverable table below is the component applicability matrix. Deliverables 6 and 7 are N/A only for this isolated presentation shell because it owns neither authoritative operational state nor recurring institutional work; those gates must be reassessed for a live integrated V2 component. The canonical process-graph standard is applicable and met: the shell has a registered JSON workflow and generated Mermaid views. A diagram alone is not runtime evidence; the browser and server checkout supplies the behavior evidence.

## Eight-deliverable component DoD assessment

| Deliverable | State | Evidence / remaining work |
| --- | --- | --- |
| 1. Code and contracts | PARTIAL | Password verifier, owner-only configuration, LAN bind/subnet/Host/Origin/CSRF rules, session, lockout and read-only static interface are versioned. Independent reviewer evidence remains pending. |
| 2. Functionality demonstrated | PARTIAL | Offline auth/security tests plus actual Firefox and Chrome browser tests cover the local preview and current UI. The Steward's Windows Chrome login/navigation was accepted on earlier commit `d1cd6f3`; Windows-client acceptance of this latest usability delta remains pending. |
| 3. Complete versioned documentation | PASS for this slice | This specification records execution, interface, authority, dependencies, limitations, preview operation and rollback. |
| 4. Troubleshooting and recovery cookbook | PASS for code checkout | Cookbook records password setup, read-only diagnostics, expected results, failure cases, session/lockout behavior, rollback and resume procedure. |
| 5. Versioned visualization flowcharts | PASS for code paths | Generated focused Mermaid view includes local setup, network admission, authentication, rate-limit, reject, and recovery paths. |
| 6. Steward-level live operational visualization | N/A for this isolated presentation shell | V1 remains the live operational dashboard; this slice has no authoritative operational state, and fixture data cannot satisfy live-view acceptance. Reassess when V2 is integrated with a governed read-only source. |
| 7. Operational autonomy and blocker clearance | N/A for an interactive static preview | It performs no recurring institutional work and owns no durable queue, worker, heartbeat, or escalation. Manual local startup is only for the preview. Integration/acceptance blockers are recorded in issue #164. |
| 8. Registered canonical process graph | PASS | `process_graphs/riverview-v2/workspace-shell.json` validates with globally unique IDs and typed runtime/diagnostic/recovery edges; generated views pass `process_graph.py check`. |

This increment adds the V2-only local ZIP flow. Snapshot download is demonstrated in Chrome against the authenticated LAN preview and the ZIP contents are inspected and matched to a selected V2 view. GitHub archival, live backend diagnostics, a pixel screenshot inside the ZIP, and resident chat remain disconnected; the package states these omissions explicitly.

**Overall:** the preview remains **PARTIAL / not a production release**. LAN login and basic navigation were previously accepted by the Steward on `d1cd6f3`; the V2 Snapshot passes authenticated local Chrome LAN acceptance; Windows Chrome confirmation of this new Snapshot control and independent code review remain pending. This does not authorize live V2 data, merge, Nginx changes, firewall changes, or deployment as a production service.

### Cross-cutting gates

- **Execution model:** interactive browser shell plus request-driven foreground static preview. Session and failed-login state are in memory and reset on restart; the password hash remains in the owner-only local config file. No recurring work source or autonomous task is represented.
- **External observability:** N/A for an independently operated service because there is no service lifecycle or authoritative V2 status. The local startup URL and HTTP status are diagnostic only and are not health/heartbeat claims. V1 retains its own observability contract.
- **Blockers:** Windows Chrome confirmation of this new Snapshot control; independent code review; future V2 resident/resource data contract, governed account identity, GitHub archive authorization, and live diagnostics contract. The preview password was already commissioned; no production action is pending or performed here.

## V2 preview usability increment and feature-parity register

| V1 capability | V2 preview status | Truthful state / next dependency |
| --- | --- | --- |
| Live Dashboard / Grace / CME status and freshness | Not integrated | V1 remains authoritative; V2 fixtures are not live status. Needs an approved read-only projection, identity and authorization contract. |
| Account login and Steward authorization | Preview-only LAN password | Separate local preview auth; no V1 session reuse or production identity integration. |
| Diagnostic Snapshot | Enabled `Snapshot` control creates a local ZIP | Bounded V2 fixture/browser state and manifest are included; no upload or live data. GitHub archive needs a separately reviewed V2 auth/API contract. |
| Resident conversation / Grace chat | Not connected | V1 API contract states conversation routes are not implemented. Needs authenticated resident-bound API, persistence, privacy/retention, authorization and failure/event contracts. |
| ChatGPT external client | External link only | Opens chatgpt.com; no Riverview context transfer or Grace connection. |
| Comms5 communication channel | Disconnected status only | No endpoint or credentials are integrated. |
| Fixture navigation/resources/knowledge | Implemented locally | Synthetic/read-only fixture content only; selection stays in memory. |
| Theme and sidebars | Implemented in V2 preview | Light/Dark/System; left and right independently cycle expanded/compact/hidden; theme choice alone persists locally. |

The local Snapshot feature is implemented and tested. Archive-to-GitHub, live server diagnostics, pixel screenshot capture, resident conversations, V1 endpoint use, dashboard projection, and V2 account identity remain unconnected. No V1 endpoint, credential, or archive implementation was changed.

This is not a claim that issue #164 or a deployed V2 component is fully accepted.


## Dashboard-integrated Snapshot mode

The dashboard release may serve this shell under `/v2/`. Relative asset paths work in both the dashboard path and standalone preview. At `/v2/`, Snapshot uses the current dashboard origin, account session and CSRF protection to obtain the shared operational projections and submit the same generated ZIP to the existing archive API. The V2 state is allowlisted from the rendered shell; shared dashboard status and snapshot projections remain common. The manifest uses `rv.website.diagnostic-snapshot.v1`, identifies `dashboard_version: v2`, and carries the capture ID, UTC time, source commit and deployment ID. Asset names use `riverview-v2-<timestamp>-<capture-id>.zip`. The same Blob is archived and downloaded.

The standalone LAN preview stays separate, fixture-only, and local-download-only. It does not gain API or GitHub authority. Integrated mode requires the dashboard origin and a current Steward session; missing authentication or CSRF denies API access. GitHub credentials remain exclusively in the dashboard server.

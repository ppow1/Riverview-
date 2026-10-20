<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.3
Purpose: Specify the isolated V2 browser shell and password-protected LAN preview
Authority: Fixture presentation only; no institutional or production authority
Changed: 2026-10-20 UTC | RV-WEB-V2-LAN-PREVIEW-001 | Document password-protected trusted-LAN preview
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell

**Tasks:** `RV-WEB-V2-SHELL-001` (fixture shell) and `RV-WEB-V2-LAN-PREVIEW-001` (authenticated LAN access) · **Owner:** Windows C1 · **Classification:** isolated frontend enhancement / preview operation.  
**Component:** `RIVERVIEW-V2-WORKSPACE-SHELL` · **Milestone:** issue #164 parallel V2 shell.  
**Execution model:** static browser assets served by an optional foreground Python preview process. The LAN option uses request-driven in-memory session and rate-limit state. No systemd unit, database, production API, or worker.

## Ready, design, and boundaries

Issue #164 requests a parallel workspace-first interface while V1 remains the default. This task provides the first shell slice: compact navigation; resident directory selection; persistent resident/conversation context; and overview, work, resources, knowledge, ChatGPT, and Comms5 surfaces. A session-scoped in-memory selection survives view changes. All content is visibly identified as fixture or preview data. Grace is represented only by a verified name from the requested shell context; this does not assert a live resident profile or expose Grace data. Other residents and work items are synthetic.

The shell has no network-data path. By default its preview server binds only to loopback and serves only `website/v2`. The optional LAN mode binds to one explicit IPv4 address, requires a narrow client subnet and a local password hash file, and checks the Host header, Origin, and client address. It serves only this static shell and rejects mutating methods other than the password form. The shell retains a `connect-src 'none'` policy. ChatGPT is an explicit external link; Comms5 is a noninteractive disconnected status. Message, dispatch, and other state-changing controls are disabled. No bearer token, production API, browser storage, or browser-held password is used.

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
3. LAN mode binds only to the explicit Camrui IPv4 address, checks the configured /24 and Host, and requires password auth before serving any shell asset.
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
| Automated checkout | Offline auth/security tests, syntax, browser layouts, graph consistency, revision/backup audit, and V1 isolation smoke are recorded per source commit. | PASS for local code checkout; actual Windows-client acceptance pending |
| Code review | Author self-review covers browser authority, network, method, path, and production isolation boundaries. | PARTIAL; independent review requested through the draft PR if an authorized reviewer is available |
| Deployment / acceptance | Steward authorized this isolated LAN preview. No V1, Nginx, firewall, systemd, traffic, production API, or live data change is included. Actual Windows browser acceptance requires local password setup and a user-side test. | PARTIAL pending the Windows test |
| Operations / maintenance | The foreground preview can be stopped/restarted locally; sessions and lockouts reset on restart. No durable queue or autonomous work exists. | N/A for the static preview; document explicit resume/rollback in the cookbook |

The Rev 1.6 eight-deliverable table below is the component applicability matrix. Deliverables 6 and 7 are N/A only for this isolated presentation shell because it owns neither authoritative operational state nor recurring institutional work; those gates must be reassessed for a live integrated V2 component. The canonical process-graph standard is applicable and met: the shell has a registered JSON workflow and generated Mermaid views. A diagram alone is not runtime evidence; the browser and server checkout supplies the behavior evidence.

## Eight-deliverable component DoD assessment

| Deliverable | State | Evidence / remaining work |
| --- | --- | --- |
| 1. Code and contracts | PARTIAL | Password verifier, owner-only configuration, LAN bind/subnet/Host/Origin rules, session, lockout and read-only static interface are versioned. Independent reviewer evidence remains pending. |
| 2. Functionality demonstrated | PARTIAL | Offline tests cover normal login, unauthorized assets, bad password, session signature/expiry, lockout, configuration permissions, Host/Origin/subnet and method/path rejection. Actual Windows development-PC browser acceptance is not yet available. |
| 3. Complete versioned documentation | PASS for this slice | This specification records execution, interface, authority, dependencies, limitations, preview operation and rollback. |
| 4. Troubleshooting and recovery cookbook | PASS for code checkout | Cookbook records password setup, read-only diagnostics, expected results, failure cases, session/lockout behavior, rollback and resume procedure. |
| 5. Versioned visualization flowcharts | PASS for code paths | Generated focused Mermaid view includes local setup, network admission, authentication, rate-limit, reject, and recovery paths. |
| 6. Steward-level live operational visualization | N/A for this isolated presentation shell | V1 remains the live operational dashboard; this slice has no authoritative operational state, and fixture data cannot satisfy live-view acceptance. Reassess when V2 is integrated with a governed read-only source. |
| 7. Operational autonomy and blocker clearance | N/A for an interactive static preview | It performs no recurring institutional work and owns no durable queue, worker, heartbeat, or escalation. Manual local startup is only for the preview. Integration/acceptance blockers are recorded in issue #164. |
| 8. Registered canonical process graph | PASS | `process_graphs/riverview-v2/workspace-shell.json` validates with globally unique IDs and typed runtime/diagnostic/recovery edges; generated views pass `process_graph.py check`. |

**Overall:** the isolated preview and password-auth implementation are **NOT DONE as user-accepted LAN access** until the Steward sets the local password and verifies Chrome from Windows. Independent review is pending. This does not authorize live V2 data, merge, Nginx changes, firewall changes, or deployment as a production service.

### Cross-cutting gates

- **Execution model:** interactive browser shell plus request-driven foreground static preview. Session and failed-login state are in memory and reset on restart; the password hash remains in the owner-only local config file. No recurring work source or autonomous task is represented.
- **External observability:** N/A for an independently operated service because there is no service lifecycle or authoritative V2 status. The local startup URL and HTTP status are diagnostic only and are not health/heartbeat claims. V1 retains its own observability contract.
- **Blockers:** Steward local password setup and Windows Chrome acceptance; independent code review; future V2 resident/resource data contract and governed auth decision. No production action is pending or performed by this preview.

This is not a claim that issue #164 or a deployed V2 component is fully accepted.

<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.1
Purpose: Specify the isolated V2 browser shell preview
Authority: Fixture presentation only; no institutional or production authority
Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Map acceptance to all eight Rev 1.6 deliverables
History: Git and revision/backup manifest
-->
# Riverview V2 workspace shell

**Task:** `RV-WEB-V2-SHELL-001` · **Owner:** C1 · **Classification:** isolated UI implementation / preview.  
**Component:** `RIVERVIEW-V2-WORKSPACE-SHELL` · **Milestone:** issue #164 parallel V2 shell.  
**Execution model:** static browser assets served by an optional local Python preview process. No systemd unit, database, production API, worker, authentication, or persistence.

## Ready, design, and boundaries

Issue #164 requests a parallel workspace-first interface while V1 remains the default. This task provides the first shell slice: compact navigation; resident directory selection; persistent resident/conversation context; and overview, work, resources, knowledge, ChatGPT, and Comms5 surfaces. A session-scoped in-memory selection survives view changes. All content is visibly identified as fixture or preview data. Grace is represented only by a verified name from the requested shell context; this does not assert a live resident profile or expose Grace data. Other residents and work items are synthetic.

The shell has no network-data path. Its preview server is loopback-only, serves only `website/v2`, applies a `connect-src 'none'` policy, and rejects mutating HTTP methods. ChatGPT is an explicit external link; Comms5 is a noninteractive disconnected status. Message, dispatch, and other state-changing controls are disabled. No token, API contract, storage, or browser-to-service credential is present.

The existing V1 is a Python standard-library service with static assets, a bearer-protected `rv.dashboard.v1` API, read-only PostgreSQL projections, and narrowly scoped notification-receipt writes. It is deployed separately from this code. This implementation does not reuse or call its API. V1 stays unchanged and is not a dependency.

## Interfaces and operations

Run from a checkout:

```sh
python3 scripts/serve_v2_workspace_preview.py --host 127.0.0.1 --port 8877
```

Open `http://127.0.0.1:8877/` on the checkout host. For a Steward browser on another LAN workstation, use an authenticated SSH local forward to Camrui and browse to that workstation's loopback URL; no listener or firewall change is needed. The process is foreground-only and stops with Ctrl-C. It is a developer preview, not a deployment artifact or production service.

Future authoritative residents, assignments, work, model/resource controls, and communications need explicit API contracts, governed identity/authorization, privacy review, and component acceptance. Do not substitute fixtures for those contracts or infer permission from a visible action.

## Acceptance criteria and evidence

1. V1 source and runtime remain unchanged.
2. V2 serves only static files on loopback and refuses unsafe methods/path escapes.
3. Navigation and resident selection work in browser memory; view switching retains selected context.
4. No production host/API reference or browser network connection exists.
5. Desktop and phone layouts fit their viewport; browser interaction latency is measured on the actual preview.
6. Recovery is local: stop and restart the preview command. No migration or rollback of V1 is involved.

Run the offline and browser checks from the checkout root:

```sh
python3 -m unittest tests.test_v2_workspace_shell -v
python3 scripts/verify_v2_workspace_browser.py --base-url http://127.0.0.1:8877
node scripts/verify_v2_workspace_mobile.cjs --url http://127.0.0.1:8877/
python3 scripts/process_graph.py validate
python3 scripts/process_graph.py check
```

Browser navigation timings measure the synchronous in-memory view switch handler; viewport width/overflow checks measure actual rendered layout. They do not claim API load or production readiness.

See [troubleshooting and recovery](RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md) and the generated [shell process flow](RIVERVIEW_V2_WORKSPACE_SHELL_FLOW.md). Structural process-graph consistency is checked by `python3 scripts/process_graph.py check`; automated and browser verification commands are recorded with issue #164.

## Eight-deliverable component DoD assessment

| Deliverable | State | Evidence / remaining work |
| --- | --- | --- |
| 1. Code and contracts | PARTIAL | Local implementation and interface/security contract are defined and reviewed. No commit/PR or independent code reviewer evidence yet. |
| 2. Functionality demonstrated | PASS for the declared Camrui local preview | Loopback server and Firefox/Chrome browser tests cover normal navigation, resident selection, context retention, unsafe methods, traversal rejection, browser errors, and desktop/390px layout. No production deployment is claimed. |
| 3. Complete versioned documentation | PASS for this slice | This specification records execution, interface, authority, dependencies, limitations, preview operation and rollback. |
| 4. Troubleshooting and recovery cookbook | PASS for this slice | Cookbook records read-only diagnostics, expected results, failure cases and local resume procedure. |
| 5. Versioned visualization flowcharts | PASS | Generated focused Mermaid view describes normal, decision, rejection, stop, and restart paths. |
| 6. Steward-level live operational visualization | N/A for this isolated presentation shell | V1 remains the live operational dashboard; this slice has no authoritative operational state, and fixture data cannot satisfy live-view acceptance. Reassess when V2 is integrated with a governed read-only source. |
| 7. Operational autonomy and blocker clearance | N/A for an interactive static preview | It performs no recurring institutional work and owns no durable queue, worker, heartbeat, or escalation. Manual local startup is only for the preview. Integration/acceptance blockers are recorded in issue #164. |
| 8. Registered canonical process graph | PASS | `process_graphs/riverview-v2/workspace-shell.json` validates with globally unique IDs and typed runtime/diagnostic/recovery edges; generated views pass `process_graph.py check`. |

**Overall:** the issue's isolated preview slice is demonstrated; the V2 component release is **NOT DONE**. The code remains an uncommitted local checkout, independent review and Steward acceptance are outstanding, and no live V2 data contract or deployment has been authorized.

### Cross-cutting gates

- **Execution model:** interactive browser shell plus request-driven foreground static preview. No recurring work source, retry loop, persistence, or human follow-up is represented as autonomous behavior. Repeated navigation is browser-tested; server restart resets only preview memory.
- **External observability:** N/A for an independently operated service because there is no service lifecycle or authoritative V2 status. The local startup URL and HTTP status are diagnostic only and are not health/heartbeat claims. V1 retains its own observability contract.
- **Blockers:** resident/assignment source contract, governed identity/authorization, V2 live Steward view integration, independent code review, and explicit Steward acceptance before deployment. Owners/authorization are tracked on issue #164; no production action is pending or performed by this preview.

This is not a claim that issue #164 or a deployed V2 component is fully accepted.

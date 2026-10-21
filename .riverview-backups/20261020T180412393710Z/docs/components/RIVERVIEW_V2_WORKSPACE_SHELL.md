<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Component: RIVERVIEW-V2-WORKSPACE-SHELL
File Revision: 1.0.0
Purpose: Specify the isolated V2 browser shell preview
Authority: Fixture presentation only; no institutional or production authority
Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Initial V2 shell specification
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

See [troubleshooting and recovery](RIVERVIEW_V2_WORKSPACE_SHELL_COOKBOOK.md) and the generated [shell process flow](RIVERVIEW_V2_WORKSPACE_SHELL_FLOW.md). Structural process-graph consistency is checked by `python3 scripts/process_graph.py check`; automated and browser verification commands are recorded with issue #164.

## Eight-deliverable component DoD assessment

| Deliverable | State | Evidence / remaining work |
| --- | --- | --- |
| A. Code and contracts | Complete for static slice | Static assets, loopback preview server, no API/persistence/auth, CSP and method denial. Future live API contract is explicitly out of scope. |
| B. Demonstrated function | Complete for preview | Automated server checks and local browser interaction, error-free navigation, responsive viewport measurements. No live institutional data or authorized deployment. |
| C. Versioned documentation | Complete for this slice | This specification, operation and limitations, rollback, and versioned process graph. |
| D. Troubleshooting and recovery | Complete for this slice | Cookbook below. |
| E. Versioned process flow | Complete | Canonical JSON and generated focused Mermaid/aggregate graph. |
| F. Monitoring, alerts, and operator views | Not applicable to a manually run static preview | No autonomous service or operational signal exists. Reassess for any persistent deployment. |
| G. Resource/maintenance/cost model | Not applicable to the local preview | Python standard library only; no service, database, cloud, or paid dependency. Reassess before shared deployment. |
| H. Acceptance, recovery, and lifecycle evidence | Partial | Checkout and local browser evidence can establish this preview. Steward acceptance and deployment acceptance remain open; no production change was authorized. |

This is not a claim that issue #164 or a deployed V2 component is fully accepted.
